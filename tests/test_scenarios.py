import asyncio
import json
import os
import sys
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import strings, web_server
from phasmid.capabilities import Capability
from phasmid.restricted_actions import (
    RestrictedActionPolicy,
    RestrictedActionRejected,
    evaluate_restricted_action,
)

SCENARIO_PATH = os.path.join(ROOT, "tests", "scenarios", "restricted_flows.json")


def load_scenarios():
    with open(SCENARIO_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_repo_text(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as handle:
        return handle.read()


class RestrictedFlowScenarioTests(unittest.TestCase):
    def tearDown(self):
        web_server._rate_limit.clear()
        web_server._restricted_sessions.clear()

    def test_required_scenarios_are_defined(self):
        scenario_ids = {scenario["id"] for scenario in load_scenarios()}
        self.assertEqual(
            {
                "hidden-restricted-route-before-confirmation",
                "restricted-action-without-password-reentry",
                "object-cue-mismatch-before-retrieve",
                "field-mode-maintenance-without-confirmation",
                "container-initialization-after-valid-confirmation",
                "local-access-path-clear-after-valid-confirmation",
                "stale-restricted-session-rejection",
                "rapid-local-clear-without-confirmation",
            },
            scenario_ids,
        )

    def test_scenarios_reference_documented_procedures(self):
        for scenario in load_scenarios():
            with self.subTest(scenario=scenario["id"]):
                refs = scenario.get("procedure_refs")
                self.assertTrue(refs, "scenario must define procedure_refs")
                for ref in refs:
                    with self.subTest(path=ref["path"]):
                        doc = read_repo_text(ref["path"])
                        self.assertIn(ref["text"], doc)

    def test_policy_scenarios(self):
        scenarios = [
            scenario
            for scenario in load_scenarios()
            if scenario["kind"] == "restricted_policy"
        ]
        policies = {
            "clear_unmatched_entry": RestrictedActionPolicy(
                action_id="clear_unmatched_entry",
                capability=Capability.RESTRICTED_ACTION,
                confirmation_phrase="CLEAR LOCAL ENTRY",
            ),
            "password_guarded_action": RestrictedActionPolicy(
                action_id="password_guarded_action",
                capability=Capability.RESTRICTED_ACTION,
                confirmation_phrase="CONFIRM",
                require_password_reentry=True,
            ),
            "rapid_local_clear": RestrictedActionPolicy(
                action_id="rapid_local_clear",
                capability=Capability.RAPID_LOCAL_CLEAR,
                confirmation_phrase="BRICK",
                require_restricted_confirmation=False,
            ),
        }

        for scenario in scenarios:
            with self.subTest(scenario=scenario["id"]):
                with self.assertRaises(RestrictedActionRejected) as ctx:
                    evaluate_restricted_action(
                        policies[scenario["action"]],
                        capability_allowed=scenario["capability_allowed"],
                        restricted_confirmed=scenario["restricted_confirmed"],
                        confirmation=scenario["confirmation"],
                        password_reentered=scenario.get("password_reentered", True),
                    )
                self.assertEqual(ctx.exception.message, scenario["expected_error"])

    def test_object_cue_mismatch_before_retrieve(self):
        scenario = _scenario("object-cue-mismatch-before-retrieve")

        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/retrieve"),
            )
            with mock.patch.object(
                web_server,
                "get_gesture_sequence",
                return_value=[web_server.gate.MATCH_NONE],
            ):
                web_server.gate.last_match_mode = web_server.gate.MATCH_NONE
                response = await web_server.retrieve(request, password="pw")
            self.assertEqual(response["error"], scenario["expected_error"])

        asyncio.run(run())

    def test_field_mode_maintenance_scenario(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
            )
            with (
                mock.patch.object(web_server, "field_mode_enabled", return_value=True),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=False
                ),
            ):
                response = await web_server.maintenance_page(request)
            self.assertTrue(response.context["field_mode"])
            self.assertFalse(response.context["restricted_confirmed"])

        asyncio.run(run())

    def test_valid_restricted_route_scenarios(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/emergency"),
            )
            with (
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=True
                ),
                mock.patch.object(
                    web_server.vault, "format_container"
                ) as format_container,
                mock.patch.object(
                    web_server.gate, "clear_references", return_value=(True, "ok")
                ),
                mock.patch.object(web_server.vault, "silent_brick") as silent_brick,
            ):
                init_response = await web_server.emergency_initialize(
                    request,
                    confirmation="INITIALIZE LOCAL CONTAINER",
                )
                clear_response = await web_server.emergency_brick(
                    request,
                    confirmation="CLEAR LOCAL ACCESS PATH",
                )

            format_container.assert_called_once_with(rotate_access_key=True)
            silent_brick.assert_called_once()
            self.assertEqual(init_response["status"], strings.CONTAINER_INITIALIZED)
            self.assertEqual(
                clear_response["status"], strings.LOCAL_ACCESS_PATH_CLEARED
            )

        asyncio.run(run())

    def test_stale_restricted_session_rejection(self):
        request = SimpleNamespace(
            client=SimpleNamespace(host="127.0.0.1"),
            cookies={web_server.RESTRICTED_SESSION_COOKIE: "stale-token"},
        )
        web_server._restricted_sessions["stale-token"] = {
            "client_id": "127.0.0.1",
            "expires_at": time.time() - 1,
        }

        with self.assertRaises(HTTPException) as ctx:
            web_server.require_restricted_confirmation(request)

        self.assertEqual(ctx.exception.detail, strings.RESTRICTED_CONFIRMATION_REQUIRED)


def _scenario(scenario_id):
    for scenario in load_scenarios():
        if scenario["id"] == scenario_id:
            return scenario
    raise AssertionError(f"scenario not found: {scenario_id}")


if __name__ == "__main__":
    unittest.main()
