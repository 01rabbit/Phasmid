import os
import sys
import tempfile
import time
import unittest
import unittest.mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.approval_flow import (
    DUAL_APPROVAL_ACTIONS,
    ApprovalFlowResult,
    ApprovalGrant,
    ApprovalRequest,
    DualApprovalGate,
)
from phasmid.roles import RoleStore


def _make_store(tmp):
    store = RoleStore(state_path=tmp)
    store.configure_supervisor("supervisor-passphrase-ok")
    return store


VALID_ACTION = "clear_local_access_path"
INVALID_ACTION = "not_a_real_action"
SUPERVISOR_PW = "supervisor-passphrase-ok"
WRONG_PW = "wrong-passphrase"


class TestApprovalRequest(unittest.TestCase):
    def test_not_expired_when_fresh(self):
        req = ApprovalRequest(
            action_id=VALID_ACTION,
            nonce="abc",
            created_at=time.monotonic(),
            ttl_seconds=300,
        )
        self.assertFalse(req.is_expired())

    def test_expired_when_ttl_elapsed(self):
        req = ApprovalRequest(
            action_id=VALID_ACTION,
            nonce="abc",
            created_at=time.monotonic() - 400,
            ttl_seconds=300,
        )
        self.assertTrue(req.is_expired())


class TestApprovalGrant(unittest.TestCase):
    def test_not_expired_when_fresh(self):
        grant = ApprovalGrant(
            action_id=VALID_ACTION,
            nonce="abc",
            granted_at=time.monotonic(),
            ttl_seconds=60,
        )
        self.assertFalse(grant.is_expired())

    def test_expired_after_ttl(self):
        grant = ApprovalGrant(
            action_id=VALID_ACTION,
            nonce="abc",
            granted_at=time.monotonic() - 120,
            ttl_seconds=60,
        )
        self.assertTrue(grant.is_expired())


class TestDualApprovalGate(unittest.TestCase):
    def setUp(self):
        self.gate = DualApprovalGate()
        self.tmp_dir = tempfile.mkdtemp()
        self.role_store = _make_store(self.tmp_dir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # requires_dual_approval
    # ------------------------------------------------------------------

    def test_known_actions_require_dual_approval(self):
        for action in DUAL_APPROVAL_ACTIONS:
            self.assertTrue(self.gate.requires_dual_approval(action))

    def test_unknown_action_does_not_require_dual_approval(self):
        self.assertFalse(self.gate.requires_dual_approval(INVALID_ACTION))

    # ------------------------------------------------------------------
    # request()
    # ------------------------------------------------------------------

    def test_request_for_valid_action_succeeds(self):
        result = self.gate.request(VALID_ACTION)
        self.assertIsInstance(result, ApprovalFlowResult)
        self.assertTrue(result.ok)
        self.assertEqual(result.reason, "request_created")
        self.assertTrue(len(result.nonce) > 0)

    def test_request_for_invalid_action_fails(self):
        result = self.gate.request(INVALID_ACTION)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "not_required")

    def test_second_request_while_pending_returns_error(self):
        self.gate.request(VALID_ACTION)
        result = self.gate.request(VALID_ACTION)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "already_pending")

    def test_request_after_expiry_creates_new_request(self):
        r1 = self.gate.request(VALID_ACTION)
        # Expire the pending request manually
        req = self.gate._pending[VALID_ACTION]
        expired_req = ApprovalRequest(
            action_id=req.action_id,
            nonce=req.nonce,
            created_at=time.monotonic() - 400,
            ttl_seconds=300,
        )
        self.gate._pending[VALID_ACTION] = expired_req

        r2 = self.gate.request(VALID_ACTION)
        self.assertTrue(r2.ok)
        self.assertNotEqual(r1.nonce, r2.nonce)

    def test_nonce_is_random_hex(self):
        r1 = self.gate.request(VALID_ACTION)
        # Expire and re-request
        self.gate._pending.clear()
        r2 = self.gate.request(VALID_ACTION)
        self.assertNotEqual(r1.nonce, r2.nonce)

    # ------------------------------------------------------------------
    # grant()
    # ------------------------------------------------------------------

    def test_grant_with_correct_passphrase_succeeds(self):
        r = self.gate.request(VALID_ACTION)
        g = self.gate.grant(r.nonce, SUPERVISOR_PW, self.role_store)
        self.assertTrue(g.ok)
        self.assertEqual(g.reason, "granted")

    def test_grant_with_wrong_passphrase_is_rejected(self):
        r = self.gate.request(VALID_ACTION)
        g = self.gate.grant(r.nonce, WRONG_PW, self.role_store)
        self.assertFalse(g.ok)
        self.assertEqual(g.reason, "wrong_passphrase")

    def test_grant_with_unknown_nonce_returns_no_request(self):
        g = self.gate.grant("deadbeef" * 4, SUPERVISOR_PW, self.role_store)
        self.assertFalse(g.ok)
        self.assertEqual(g.reason, "no_request")

    def test_grant_with_expired_request_returns_request_expired(self):
        r = self.gate.request(VALID_ACTION)
        req = self.gate._pending[VALID_ACTION]
        expired = ApprovalRequest(
            action_id=req.action_id,
            nonce=req.nonce,
            created_at=time.monotonic() - 400,
            ttl_seconds=300,
        )
        self.gate._pending[VALID_ACTION] = expired
        g = self.gate.grant(r.nonce, SUPERVISOR_PW, self.role_store)
        self.assertFalse(g.ok)
        self.assertEqual(g.reason, "request_expired")

    def test_grant_when_supervisor_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            unconfigured_store = RoleStore(state_path=tmp)
        r = self.gate.request(VALID_ACTION)
        g = self.gate.grant(r.nonce, SUPERVISOR_PW, unconfigured_store)
        self.assertFalse(g.ok)
        self.assertEqual(g.reason, "supervisor_not_configured")

    # ------------------------------------------------------------------
    # consume()
    # ------------------------------------------------------------------

    def test_full_flow_succeeds(self):
        r = self.gate.request(VALID_ACTION)
        self.gate.grant(r.nonce, SUPERVISOR_PW, self.role_store)
        c = self.gate.consume(VALID_ACTION, r.nonce)
        self.assertTrue(c.ok)
        self.assertEqual(c.reason, "consumed")

    def test_consume_is_single_use(self):
        r = self.gate.request(VALID_ACTION)
        self.gate.grant(r.nonce, SUPERVISOR_PW, self.role_store)
        self.gate.consume(VALID_ACTION, r.nonce)
        # Second consume must fail
        c2 = self.gate.consume(VALID_ACTION, r.nonce)
        self.assertFalse(c2.ok)

    def test_consume_without_grant_fails(self):
        r = self.gate.request(VALID_ACTION)
        c = self.gate.consume(VALID_ACTION, r.nonce)
        self.assertFalse(c.ok)
        self.assertEqual(c.reason, "no_grant")

    def test_consume_with_wrong_action_id_fails(self):
        r = self.gate.request(VALID_ACTION)
        self.gate.grant(r.nonce, SUPERVISOR_PW, self.role_store)
        c = self.gate.consume("initialize_container", r.nonce)
        self.assertFalse(c.ok)
        self.assertEqual(c.reason, "action_mismatch")

    def test_consume_expired_grant_fails(self):
        r = self.gate.request(VALID_ACTION)
        self.gate.grant(r.nonce, SUPERVISOR_PW, self.role_store)
        # Expire the grant manually
        self.gate._grants[r.nonce] = ApprovalGrant(
            action_id=VALID_ACTION,
            nonce=r.nonce,
            granted_at=time.monotonic() - 120,
            ttl_seconds=60,
        )
        c = self.gate.consume(VALID_ACTION, r.nonce)
        self.assertFalse(c.ok)
        self.assertEqual(c.reason, "grant_expired")

    # ------------------------------------------------------------------
    # Stale request purge
    # ------------------------------------------------------------------

    def test_stale_requests_are_purged_on_next_call(self):
        r = self.gate.request(VALID_ACTION)
        self.gate._pending[VALID_ACTION] = ApprovalRequest(
            action_id=VALID_ACTION,
            nonce=r.nonce,
            created_at=time.monotonic() - 400,
            ttl_seconds=300,
        )
        # Any public call triggers purge
        self.gate.status(VALID_ACTION)
        self.assertNotIn(VALID_ACTION, self.gate._pending)

    # ------------------------------------------------------------------
    # status()
    # ------------------------------------------------------------------

    def test_status_no_pending_request(self):
        s = self.gate.status(VALID_ACTION)
        self.assertTrue(s["requires_dual_approval"])
        self.assertFalse(s["pending_request"])
        self.assertFalse(s["grant_available"])

    def test_status_with_pending_request(self):
        r = self.gate.request(VALID_ACTION)
        s = self.gate.status(VALID_ACTION)
        self.assertTrue(s["pending_request"])
        self.assertFalse(s["grant_available"])
        self.assertEqual(s["nonce"], r.nonce)

    def test_status_with_grant_available(self):
        r = self.gate.request(VALID_ACTION)
        self.gate.grant(r.nonce, SUPERVISOR_PW, self.role_store)
        s = self.gate.status(VALID_ACTION)
        self.assertTrue(s["grant_available"])

    def test_status_unknown_action(self):
        s = self.gate.status(INVALID_ACTION)
        self.assertFalse(s["requires_dual_approval"])

    # ------------------------------------------------------------------
    # Direct route bypass resistance
    # ------------------------------------------------------------------

    def test_consume_without_request_and_grant_always_fails(self):
        # Simulates a caller trying to skip the request/grant steps
        c = self.gate.consume(VALID_ACTION, "arbitrary-nonce")
        self.assertFalse(c.ok)

    def test_grant_nonce_cannot_be_reused_across_actions(self):
        r1 = self.gate.request(VALID_ACTION)
        self.gate.grant(r1.nonce, SUPERVISOR_PW, self.role_store)

        # Attempt to reuse the same nonce for a different action
        self.gate.request("initialize_container")
        # Replace the new request's nonce with the old one (tampering attempt)
        self.gate._pending["initialize_container"] = ApprovalRequest(
            action_id="initialize_container",
            nonce=r1.nonce,
            created_at=time.monotonic(),
            ttl_seconds=300,
        )
        c = self.gate.consume("initialize_container", r1.nonce)
        # Grant was for VALID_ACTION, not initialize_container → action_mismatch
        self.assertFalse(c.ok)


if __name__ == "__main__":
    unittest.main()
