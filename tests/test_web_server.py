import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import web_server


class WebServerBoundaryTests(unittest.TestCase):
    def tearDown(self):
        web_server._rate_limit.clear()
        web_server._restricted_sessions.clear()
        web_server._access_attempts._state.clear()

    def test_require_web_token_rejects_invalid_token(self):
        with self.assertRaises(HTTPException) as ctx:
            web_server.require_web_token("wrong")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_require_web_token_accepts_current_token(self):
        self.assertIsNone(web_server.require_web_token(web_server.WEB_TOKEN))

    def test_disabled_capability_rejects_with_neutral_error(self):
        with mock.patch.object(web_server, "capability_enabled", return_value=False):
            with self.assertRaises(HTTPException) as ctx:
                web_server.require_capability(web_server.Capability.TOKEN_ROTATION)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "operation unavailable")

    def test_fastapi_debug_is_disabled_by_default(self):
        self.assertFalse(web_server.app.debug)

    def test_security_headers_are_applied_to_responses(self):
        response = web_server._apply_security_headers(JSONResponse({"ok": True}))
        self.assertEqual(
            response.headers["cache-control"],
            "no-store, no-cache, must-revalidate, max-age=0",
        )
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertIn(
            "frame-ancestors 'none'", response.headers["content-security-policy"]
        )
        self.assertIn("camera=(self)", response.headers["permissions-policy"])

    def test_rate_limit_blocks_after_configured_limit(self):
        request = SimpleNamespace(
            client=SimpleNamespace(host="127.0.0.1"),
            url=SimpleNamespace(path="/retrieve"),
        )
        for _ in range(web_server.RATE_LIMIT_MAX):
            web_server.enforce_rate_limit(request)

        with self.assertRaises(HTTPException) as ctx:
            web_server.enforce_rate_limit(request)
        self.assertEqual(ctx.exception.status_code, 429)

    def test_upload_size_limit_rejects_large_payload(self):
        async def run():
            with mock.patch.object(web_server, "MAX_UPLOAD_BYTES", 8):
                content = b"x" * 9
                upload = UploadFile(filename="oversized.bin", file=_BytesFile(content))
                with self.assertRaises(HTTPException) as ctx:
                    await web_server.read_limited_upload(upload)
            self.assertEqual(ctx.exception.status_code, 413)

        asyncio.run(run())

    def test_store_rejects_short_access_password(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/store"),
            )
            upload = UploadFile(filename="payload.txt", file=_BytesFile(b"data"))
            response = await web_server.store(
                request,
                file=upload,
                password="short",
                restricted_recovery_password="another-short",
            )
            self.assertIn("at least", response["error"])

        asyncio.run(run())

    def test_status_uses_neutral_terms(self):
        with mock.patch.object(
            web_server.access_cue_service,
            "status",
            return_value={
                "object_detected": True,
                "matched_mode": "dummy",
                "match_states": {"dummy": True, "secret": False},
                "registered_modes": {"dummy": True, "secret": False},
            },
        ):
            status = web_server.neutral_status()

        self.assertEqual(status["object_state"], "matched")
        self.assertEqual(
            set(status.keys()),
            {"camera_ready", "object_state", "device_state", "local_mode"},
        )

    def test_require_ui_unlock_rejects_locked_face_session(self):
        request = SimpleNamespace(
            client=SimpleNamespace(host="127.0.0.1"),
            cookies={},
        )
        with (
            mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True),
            mock.patch.object(
                web_server.ui_face_lock_service, "session_valid", return_value=False
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                web_server.require_ui_unlock(request)
        self.assertEqual(ctx.exception.status_code, 423)

    def test_face_verify_sets_session_cookie(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/face/verify"),
            )
            with (
                mock.patch.object(
                    web_server, "ui_face_lock_enabled", return_value=True
                ),
                mock.patch.object(
                    web_server, "_recent_camera_frames", return_value=[object()]
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service,
                    "verify_from_frames",
                    return_value=(True, "ok"),
                ) as verify,
                mock.patch.object(web_server.ui_face_lock_service, "create_session") as create,
            ):
                response = await web_server.face_verify(request)
            verify.assert_called_once()
            create.assert_called_once()
            self.assertIn(
                web_server.FACE_SESSION_COOKIE, response.headers.get("set-cookie", "")
            )

        asyncio.run(run())

    def test_locked_status_hides_camera_and_object_state(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
            )
            with (
                mock.patch.object(
                    web_server, "ui_face_lock_enabled", return_value=True
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service, "session_valid", return_value=False
                ),
                mock.patch.object(
                    web_server,
                    "neutral_status",
                    return_value={
                        "camera_ready": True,
                        "object_state": "matched",
                        "device_state": "ready",
                        "local_mode": True,
                    },
                ),
            ):
                response = await web_server.status(request)
            self.assertEqual(response["device_state"], "locked")
            self.assertFalse(response["camera_ready"])
            self.assertEqual(response["object_state"], "none")
            self.assertEqual(
                set(response.keys()),
                {"camera_ready", "object_state", "device_state", "local_mode"},
            )

        asyncio.run(run())

    def test_retrieve_attempt_limiter_blocks_repeated_failures(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/retrieve"),
            )
            limiter = web_server.AttemptLimiter(
                max_failures=1,
                lockout_seconds=30,
                clock=lambda: 1000,
            )
            with (
                mock.patch.object(web_server, "_access_attempts", limiter),
                mock.patch.object(
                    web_server.access_cue_service,
                    "auth_sequence",
                    return_value=[web_server.access_cue_service.match_none()],
                ),
                mock.patch.object(
                    web_server.access_cue_service,
                    "current_match_mode",
                    return_value=web_server.access_cue_service.match_none(),
                ),
            ):
                first = await web_server.retrieve(request, password="wrong-passphrase")
                second = await web_server.retrieve(request, password="wrong-passphrase")
            self.assertEqual(first["error"], web_server.text.NO_VALID_ENTRY_FOUND)
            self.assertEqual(
                second["error"],
                web_server.text.ACCESS_TEMPORARILY_UNAVAILABLE,
            )

        asyncio.run(run())

    def test_video_feed_requires_unlocked_ui(self):
        route = next(
            route
            for route in web_server.app.routes
            if getattr(route, "path", None) == "/video_feed"
        )
        dependency_names = {item.call.__name__ for item in route.dependant.dependencies}
        self.assertIn("require_ui_unlock", dependency_names)

    def test_ui_lock_video_feed_requires_face_lock_enabled(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
            )
            with mock.patch.object(
                web_server, "ui_face_lock_enabled", return_value=False
            ):
                with self.assertRaises(HTTPException) as ctx:
                    await web_server.ui_lock_video_feed(request)
            self.assertEqual(ctx.exception.status_code, 404)

        asyncio.run(run())

    def test_ui_lock_video_feed_is_available_while_locked(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
            )
            with (
                mock.patch.object(
                    web_server, "ui_face_lock_enabled", return_value=True
                ),
                mock.patch.object(
                    web_server.access_cue_service, "generate_frames", return_value=iter([b"frame"])
                ),
            ):
                response = await web_server.ui_lock_video_feed(request)
            self.assertEqual(
                response.media_type, "multipart/x-mixed-replace; boundary=frame"
            )

        asyncio.run(run())

    def test_initial_face_enroll_allows_first_time_registration(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/face/enroll"),
            )
            with (
                mock.patch.object(
                    web_server, "ui_face_lock_enabled", return_value=True
                ),
                mock.patch.object(
                    web_server, "ui_face_enrollment_enabled", return_value=False
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service, "enrollment_pending", return_value=False
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service, "is_enrolled", return_value=False
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service,
                    "enroll_from_frames",
                    return_value=(True, "ok"),
                ) as enroll,
                mock.patch.object(
                    web_server.ui_face_lock_service, "clear_enrollment_request"
                ) as clear,
            ):
                response = await web_server.face_enroll(request)
            enroll.assert_called_once()
            clear.assert_called_once_with()
            self.assertIn("status", response)

        asyncio.run(run())

    def test_initial_face_enroll_accepts_bootstrap_flag(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/face/enroll"),
            )
            with (
                mock.patch.object(
                    web_server, "ui_face_lock_enabled", return_value=True
                ),
                mock.patch.object(
                    web_server, "ui_face_enrollment_enabled", return_value=True
                ),
                mock.patch.object(
                    web_server, "_recent_camera_frames", return_value=[object()]
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service, "is_enrolled", return_value=False
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service,
                    "enroll_from_frames",
                    return_value=(True, "ok"),
                ) as enroll,
                mock.patch.object(
                    web_server.ui_face_lock_service, "clear_enrollment_request"
                ) as clear,
            ):
                response = await web_server.face_enroll(request)
            enroll.assert_called_once()
            clear.assert_called_once_with()
            self.assertIn("status", response)

        asyncio.run(run())

    def test_initial_face_enroll_accepts_reset_flag(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/face/enroll"),
            )
            with (
                mock.patch.object(
                    web_server, "ui_face_lock_enabled", return_value=True
                ),
                mock.patch.object(
                    web_server, "ui_face_enrollment_enabled", return_value=False
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service, "enrollment_pending", return_value=True
                ),
                mock.patch.object(
                    web_server, "_recent_camera_frames", return_value=[object()]
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service, "is_enrolled", return_value=False
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service,
                    "enroll_from_frames",
                    return_value=(True, "ok"),
                ) as enroll,
                mock.patch.object(
                    web_server.ui_face_lock_service, "clear_enrollment_request"
                ) as clear,
            ):
                response = await web_server.face_enroll(request)
            enroll.assert_called_once()
            clear.assert_called_once_with()
            self.assertIn("status", response)

        asyncio.run(run())

    def test_face_enroll_requires_unlock_when_replacing_existing_template(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/face/enroll"),
            )
            with (
                mock.patch.object(
                    web_server, "ui_face_lock_enabled", return_value=True
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service, "is_enrolled", return_value=True
                ),
                mock.patch.object(web_server, "_ui_unlocked", return_value=False),
                mock.patch.object(web_server.ui_face_lock_service, "enroll_from_frames") as enroll,
            ):
                response = await web_server.face_enroll(request)
            enroll.assert_not_called()
            self.assertIn("unlocked", response["error"])

        asyncio.run(run())

    def test_face_enroll_requires_restricted_confirmation_when_replacing_template(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/face/enroll"),
            )
            with (
                mock.patch.object(
                    web_server, "ui_face_lock_enabled", return_value=True
                ),
                mock.patch.object(
                    web_server.ui_face_lock_service, "is_enrolled", return_value=True
                ),
                mock.patch.object(web_server, "_ui_unlocked", return_value=True),
                mock.patch.object(web_server.ui_face_lock_service, "enroll_from_frames") as enroll,
            ):
                response = await web_server.face_enroll(request)
            enroll.assert_not_called()
            self.assertIn("Restricted confirmation required", response["error"])

        asyncio.run(run())

    def test_restricted_confirmation_sets_short_lived_cookie(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/restricted/confirm"),
            )
            response = await web_server.restricted_confirm(
                request,
                confirmation=web_server.RESTRICTED_CONFIRMATION_PHRASE,
            )
            self.assertIn(
                web_server.RESTRICTED_SESSION_COOKIE,
                response.headers.get("set-cookie", ""),
            )

        asyncio.run(run())

    def test_restricted_confirmation_rejects_missing_or_stale_session(self):
        request = SimpleNamespace(
            client=SimpleNamespace(host="127.0.0.1"),
            cookies={},
        )
        with self.assertRaises(HTTPException) as ctx:
            web_server.require_restricted_confirmation(request)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_entry_status_requires_restricted_confirmation_dependency(self):
        sensitive_paths = {"/maintenance/entry_status"}
        for path in sensitive_paths:
            route = next(
                route
                for route in web_server.app.routes
                if getattr(route, "path", None) == path
            )
            dependency_names = {
                item.call.__name__ for item in route.dependant.dependencies
            }
            self.assertIn("require_restricted_confirmation", dependency_names)

    def test_restricted_action_service_rejects_missing_confirmation_session(self):
        request = SimpleNamespace(
            client=SimpleNamespace(host="127.0.0.1"),
            cookies={},
        )
        with self.assertRaises(HTTPException) as ctx:
            web_server.require_restricted_action(
                "initialize_container",
                request,
                web_server.INITIALIZE_CONTAINER_PHRASE,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "restricted confirmation required")

    def test_emergency_page_hides_actions_before_restricted_confirmation(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
            )
            with (
                mock.patch.object(web_server, "_guard_page", return_value=None),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=False
                ),
            ):
                response = await web_server.emergency_page(request)
            self.assertFalse(response.context["restricted_confirmed"])
            self.assertEqual(response.context["restricted_session_seconds_remaining"], 0)

        asyncio.run(run())

    def test_emergency_page_reports_restricted_session_lifetime(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={web_server.RESTRICTED_SESSION_COOKIE: "token"},
            )
            with (
                mock.patch.object(web_server, "_guard_page", return_value=None),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=True
                ),
                mock.patch.object(
                    web_server,
                    "_restricted_session_seconds_remaining",
                    return_value=74,
                ),
            ):
                response = await web_server.emergency_page(request)
            self.assertTrue(response.context["restricted_confirmed"])
            self.assertEqual(response.context["restricted_session_seconds_remaining"], 74)

        asyncio.run(run())

    def test_entry_management_page_hides_status_before_restricted_confirmation(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
            )
            with (
                mock.patch.object(web_server, "_guard_page", return_value=None),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=False
                ),
            ):
                response = await web_server.entry_management_page(request)
            self.assertFalse(response.context["restricted_confirmed"])
            self.assertNotIn("entry_status", response.context)

        asyncio.run(run())

    def test_field_mode_maintenance_hides_paths_before_restricted_confirmation(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
            )
            with (
                mock.patch.object(web_server, "_guard_page", return_value=None),
                mock.patch.object(web_server, "field_mode_enabled", return_value=True),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=False
                ),
            ):
                response = await web_server.maintenance_page(request)
            self.assertTrue(response.context["field_mode"])
            self.assertFalse(response.context["restricted_confirmed"])
            self.assertEqual(response.context["state_path"], "")

        asyncio.run(run())

    def test_field_mode_diagnostics_are_neutral_before_restricted_confirmation(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/maintenance/diagnostics"),
            )
            with (
                mock.patch.object(web_server, "field_mode_enabled", return_value=True),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=False
                ),
                mock.patch.object(
                    web_server,
                    "neutral_status",
                    return_value={
                        "camera_ready": True,
                        "object_state": "none",
                        "device_state": "ready",
                        "local_mode": True,
                    },
                ),
            ):
                response = await web_server.diagnostics(request)
            self.assertEqual(
                set(response.keys()),
                {
                    "device_state",
                    "camera_ready",
                    "object_state",
                    "local_mode",
                    "restricted_confirmation_active",
                },
            )

        asyncio.run(run())

    def test_diagnostics_include_hardware_binding_details_after_restricted_access(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/maintenance/diagnostics"),
            )
            with (
                mock.patch.object(web_server, "field_mode_enabled", return_value=True),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=True
                ),
                mock.patch.object(
                    web_server,
                    "neutral_status",
                    return_value={
                        "camera_ready": True,
                        "object_state": "none",
                        "device_state": "ready",
                        "local_mode": True,
                    },
                ),
                mock.patch.object(
                    web_server,
                    "hardware_binding_status",
                    return_value=SimpleNamespace(
                        to_dict=lambda: {
                            "host_supported": True,
                            "device_binding_available": True,
                            "external_binding_configured": False,
                        }
                    ),
                ),
            ):
                response = await web_server.diagnostics(request)
            self.assertIn("hardware_binding", response)
            self.assertEqual(
                response["hardware_binding"]["device_binding_available"], True
            )

        asyncio.run(run())

    def test_field_mode_rejects_log_export_without_restricted_confirmation(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/maintenance/logs"),
            )
            with (
                mock.patch.object(web_server, "field_mode_enabled", return_value=True),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=False
                ),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    await web_server.export_logs(request)
            self.assertEqual(ctx.exception.status_code, 403)

        asyncio.run(run())

    def test_field_mode_rejects_token_rotation_without_restricted_confirmation(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/maintenance/rotate_token"),
            )
            with (
                mock.patch.object(web_server, "field_mode_enabled", return_value=True),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=False
                ),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    await web_server.rotate_token(request)
            self.assertEqual(ctx.exception.status_code, 403)

        asyncio.run(run())

    def test_deployment_mode_rejects_token_rotation_when_unavailable(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/maintenance/rotate_token"),
            )
            with mock.patch.dict(os.environ, {"PHASMID_PROFILE": "field"}, clear=True):
                with self.assertRaises(HTTPException) as ctx:
                    await web_server.rotate_token(request)
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertEqual(ctx.exception.detail, "operation unavailable")

        asyncio.run(run())

    def test_field_mode_rejects_session_reset_without_restricted_confirmation(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/maintenance/reset_session"),
            )
            with (
                mock.patch.object(web_server, "field_mode_enabled", return_value=True),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=False
                ),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    await web_server.reset_session(request)
            self.assertEqual(ctx.exception.status_code, 403)

        asyncio.run(run())

    def test_hidden_clear_requires_explicit_phrase(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/purge_other"),
            )
            with mock.patch.object(
                web_server, "_restricted_session_valid", return_value=True
            ):
                with self.assertRaises(HTTPException) as ctx:
                    await web_server.purge_other(
                        request,
                        accessed_entry="entry_1",
                        confirmation="DELETE",
                    )
            self.assertEqual(ctx.exception.detail, "confirmation rejected")

        asyncio.run(run())

    def test_hidden_clear_ignores_purge_confirmation_environment(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/purge_other"),
            )
            with (
                mock.patch.object(
                    web_server, "purge_confirmation_required", return_value=False
                ),
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=True
                ),
                mock.patch.object(web_server.vault, "purge_other_mode") as purge,
            ):
                with self.assertRaises(HTTPException) as ctx:
                    await web_server.purge_other(
                        request,
                        accessed_entry="entry_1",
                        confirmation="",
                    )
            purge.assert_not_called()
            self.assertEqual(ctx.exception.detail, "confirmation rejected")

        asyncio.run(run())

    def test_hidden_clear_accepts_confirmation_phrase(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/purge_other"),
            )
            with (
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=True
                ),
                mock.patch.object(web_server.vault, "purge_other_mode") as purge,
            ):
                response = await web_server.purge_other(
                    request,
                    accessed_entry="entry_1",
                    confirmation=web_server.DESTRUCTIVE_CLEAR_PHRASE,
                )
            purge.assert_called_once_with("dummy")
            self.assertIn("cleared", response["status"])

        asyncio.run(run())

    def test_emergency_initialize_requires_confirmation_phrase(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/emergency/initialize"),
            )
            with (
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=True
                ),
                mock.patch.object(web_server.vault, "format_container") as init,
            ):
                with self.assertRaises(HTTPException) as ctx:
                    await web_server.emergency_initialize(
                        request,
                        confirmation="INITIALIZE",
                    )
            init.assert_not_called()
            self.assertEqual(ctx.exception.detail, "confirmation rejected")

        asyncio.run(run())

    def test_emergency_initialize_resets_container_and_bindings(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/emergency/initialize"),
            )
            with (
                mock.patch.object(
                    web_server, "_restricted_session_valid", return_value=True
                ),
                mock.patch.object(web_server.vault, "format_container") as init,
                mock.patch.object(
                    web_server.access_cue_service, "clear_references", return_value=(True, "ok")
                ) as clear,
            ):
                response = await web_server.emergency_initialize(
                    request,
                    confirmation=web_server.INITIALIZE_CONTAINER_PHRASE,
                )
            init.assert_called_once_with(rotate_access_key=True)
            clear.assert_called_once_with()
            self.assertIn("initialized", response["status"])

        asyncio.run(run())

    def test_duress_mode_auto_purges_dummy_access(self):
        with (
            mock.patch.object(web_server, "duress_mode_enabled", return_value=True),
            mock.patch.object(
                web_server, "purge_confirmation_required", return_value=True
            ),
            mock.patch.object(web_server.vault, "purge_other_mode") as purge,
        ):
            self.assertTrue(web_server._maybe_auto_purge("dummy", source="test"))
        purge.assert_called_once_with("dummy")

    def test_duress_mode_does_not_auto_purge_secret_access(self):
        with (
            mock.patch.object(web_server, "duress_mode_enabled", return_value=True),
            mock.patch.object(
                web_server, "purge_confirmation_required", return_value=True
            ),
            mock.patch.object(web_server.vault, "purge_other_mode") as purge,
        ):
            self.assertFalse(web_server._maybe_auto_purge("secret", source="test"))
        purge.assert_not_called()

    def test_restricted_recovery_password_role_updates_unmatched_entry(self):
        with mock.patch.object(web_server.vault, "purge_other_mode") as purge:
            self.assertTrue(
                web_server._purge_for_password_role(
                    "dummy",
                    web_server.PhasmidVault.PURGE_ROLE,
                    source="test",
                )
            )
        purge.assert_called_once_with("dummy")

    def test_open_password_role_preserves_unmatched_entry(self):
        with mock.patch.object(web_server.vault, "purge_other_mode") as purge:
            self.assertFalse(
                web_server._purge_for_password_role(
                    "dummy",
                    web_server.PhasmidVault.OPEN_ROLE,
                    source="test",
                )
            )
        purge.assert_not_called()

    def test_download_response_uses_neutral_filename_without_state_change_header(self):
        response = web_server.create_file_response(
            b"payload", "source-name.txt", purge_applied=True
        )
        self.assertIn("retrieved_payload.bin", response.headers["content-disposition"])
        self.assertNotIn("x-local-state-updated", response.headers)
        self.assertNotIn("source-name", str(response.headers).lower())

    def test_metadata_check_reports_obvious_local_risk(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/metadata/check"),
            )
            upload = UploadFile(
                filename="notes.txt",
                file=_BytesFile(b"author: Alice\npath: /Users/alice/source.txt\n"),
            )
            response = await web_server.metadata_check(request, upload)
            self.assertEqual(response["risk"], "high")
            self.assertIn("local path leakage", response["findings"])
            self.assertIn("best-effort", response["limitation"])

        asyncio.run(run())

    def test_metadata_scrub_uses_neutral_download_name(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/metadata/scrub"),
            )
            upload = UploadFile(
                filename="revealing-name.txt",
                file=_BytesFile(b"author: Alice\npath: /home/alice/source.txt\n"),
            )
            response = await web_server.metadata_scrub(request, upload)
            headers = str(response.headers).lower()
            self.assertIn("metadata_reduced_payload.bin", headers)
            self.assertNotIn("revealing-name", headers)

        asyncio.run(run())

    def test_metadata_scrub_ignores_scrubber_filename_for_headers(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/metadata/scrub"),
            )
            upload = UploadFile(
                filename="original-name.txt",
                file=_BytesFile(b"payload"),
            )
            with mock.patch.object(
                web_server,
                "scrub_metadata",
                return_value={
                    "success": True,
                    "filename": "revealing-result-name.txt",
                    "data": b"payload",
                    "message": "ok",
                    "limitation": "best-effort",
                },
            ):
                response = await web_server.metadata_scrub(request, upload)
            headers = str(response.headers).lower()
            self.assertIn("metadata_reduced_payload.bin", headers)
            self.assertNotIn("revealing-result-name", headers)
            self.assertNotIn("original-name", headers)

        asyncio.run(run())

    def test_metadata_routes_require_web_token_and_ui_unlock(self):
        for path in {"/metadata/check", "/metadata/scrub"}:
            route = next(
                route
                for route in web_server.app.routes
                if getattr(route, "path", None) == path
            )
            dependency_names = {
                item.call.__name__ for item in route.dependant.dependencies
            }
            self.assertIn("require_web_token", dependency_names)
            self.assertIn("require_ui_unlock", dependency_names)

    def test_metadata_scrub_unsupported_type_fails_safely(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/metadata/scrub"),
            )
            upload = UploadFile(
                filename="image.jpg",
                file=_BytesFile(b"\xff\xd8Exif\x00\x00GPS"),
            )
            response = await web_server.metadata_scrub(request, upload)
            self.assertEqual(response.status_code, 422)
            body = response.body.decode("utf-8")
            self.assertIn("not supported", body)
            self.assertIn("best-effort", body)

        asyncio.run(run())


class _BytesFile:
    def __init__(self, content):
        self._content = content
        self._offset = 0

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self._content) - self._offset
        end = min(self._offset + size, len(self._content))
        chunk = self._content[self._offset : end]
        self._offset = end
        return chunk

    def close(self):
        pass


if __name__ == "__main__":
    unittest.main()
