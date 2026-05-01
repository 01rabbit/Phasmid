import asyncio
import os
import sys
import unittest
from unittest import mock
from types import SimpleNamespace

from fastapi import HTTPException, UploadFile

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm import web_server


class WebServerBoundaryTests(unittest.TestCase):
    def tearDown(self):
        web_server._rate_limit.clear()

    def test_require_web_token_rejects_invalid_token(self):
        with self.assertRaises(HTTPException) as ctx:
            web_server.require_web_token("wrong")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_require_web_token_accepts_current_token(self):
        self.assertIsNone(web_server.require_web_token(web_server.WEB_TOKEN))

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

    def test_status_uses_neutral_terms(self):
        with mock.patch.object(web_server.gate, "get_status", return_value={
            "object_detected": True,
            "matched_mode": "dummy",
            "match_states": {"dummy": True, "secret": False},
            "registered_modes": {"dummy": True, "secret": False},
        }):
            status = web_server.neutral_status()

        self.assertEqual(status["object_state"], "matched")
        self.assertEqual(
            set(status.keys()),
            {"camera_ready", "object_state", "device_state", "local_mode"},
        )

    def test_hidden_clear_requires_explicit_phrase(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/purge_other"),
            )
            response = await web_server.purge_other(
                request,
                accessed_entry="entry_1",
                confirmation="DELETE",
            )
            self.assertIn("Confirmation required", response["error"])

        asyncio.run(run())

    def test_hidden_clear_ignores_purge_confirmation_environment(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/purge_other"),
            )
            with mock.patch.object(web_server, "purge_confirmation_required", return_value=False), \
                 mock.patch.object(web_server.vault, "purge_other_mode") as purge:
                response = await web_server.purge_other(
                    request,
                    accessed_entry="entry_1",
                    confirmation="",
                )
            purge.assert_not_called()
            self.assertIn("Confirmation required", response["error"])

        asyncio.run(run())

    def test_hidden_clear_accepts_confirmation_phrase(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/purge_other"),
            )
            with mock.patch.object(web_server.vault, "purge_other_mode") as purge:
                response = await web_server.purge_other(
                    request,
                    accessed_entry="entry_1",
                    confirmation=web_server.DESTRUCTIVE_CLEAR_PHRASE,
                )
            purge.assert_called_once_with("dummy")
            self.assertIn("cleared", response["status"])

        asyncio.run(run())

    def test_duress_mode_auto_purges_dummy_access(self):
        with mock.patch.object(web_server, "duress_mode_enabled", return_value=True), \
             mock.patch.object(web_server, "purge_confirmation_required", return_value=True), \
             mock.patch.object(web_server.vault, "purge_other_mode") as purge:
            self.assertTrue(web_server._maybe_auto_purge("dummy", source="test"))
        purge.assert_called_once_with("dummy")

    def test_duress_mode_does_not_auto_purge_secret_access(self):
        with mock.patch.object(web_server, "duress_mode_enabled", return_value=True), \
             mock.patch.object(web_server, "purge_confirmation_required", return_value=True), \
             mock.patch.object(web_server.vault, "purge_other_mode") as purge:
            self.assertFalse(web_server._maybe_auto_purge("secret", source="test"))
        purge.assert_not_called()

    def test_purge_password_role_purges_alternate_profile(self):
        with mock.patch.object(web_server.vault, "purge_other_mode") as purge:
            self.assertTrue(
                web_server._purge_for_password_role(
                    "dummy",
                    web_server.GhostVault.PURGE_ROLE,
                    source="test",
                )
            )
        purge.assert_called_once_with("dummy")

    def test_open_password_role_does_not_purge_alternate_profile(self):
        with mock.patch.object(web_server.vault, "purge_other_mode") as purge:
            self.assertFalse(
                web_server._purge_for_password_role(
                    "dummy",
                    web_server.GhostVault.OPEN_ROLE,
                    source="test",
                )
            )
        purge.assert_not_called()


class _BytesFile:
    def __init__(self, content):
        self._content = content
        self._offset = 0

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self._content) - self._offset
        end = min(self._offset + size, len(self._content))
        chunk = self._content[self._offset:end]
        self._offset = end
        return chunk

    def close(self):
        pass


if __name__ == "__main__":
    unittest.main()
