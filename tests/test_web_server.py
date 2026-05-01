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
        web_server._restricted_sessions.clear()

    def test_require_web_token_rejects_invalid_token(self):
        with self.assertRaises(HTTPException) as ctx:
            web_server.require_web_token("wrong")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_require_web_token_accepts_current_token(self):
        self.assertIsNone(web_server.require_web_token(web_server.WEB_TOKEN))

    def test_fastapi_debug_is_disabled_by_default(self):
        self.assertFalse(web_server.app.debug)

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

    def test_require_ui_unlock_rejects_locked_face_session(self):
        request = SimpleNamespace(
            client=SimpleNamespace(host="127.0.0.1"),
            cookies={},
        )
        with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True), \
             mock.patch.object(web_server.face_lock, "session_valid", return_value=False):
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
            with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True), \
                 mock.patch.object(web_server, "_recent_camera_frames", return_value=[object()]), \
                 mock.patch.object(web_server.face_lock, "verify_from_frames", return_value=(True, "ok")) as verify, \
                 mock.patch.object(web_server.face_lock, "create_session") as create:
                response = await web_server.face_verify(request)
            verify.assert_called_once()
            create.assert_called_once()
            self.assertIn(web_server.FACE_SESSION_COOKIE, response.headers.get("set-cookie", ""))

        asyncio.run(run())

    def test_locked_status_hides_camera_and_object_state(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
            )
            with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True), \
                 mock.patch.object(web_server.face_lock, "session_valid", return_value=False), \
                 mock.patch.object(web_server, "neutral_status", return_value={
                     "camera_ready": True,
                     "object_state": "matched",
                     "device_state": "ready",
                     "local_mode": True,
                 }):
                response = await web_server.status(request)
            self.assertEqual(response["device_state"], "locked")
            self.assertFalse(response["camera_ready"])
            self.assertEqual(response["object_state"], "none")
            self.assertEqual(
                set(response.keys()),
                {"camera_ready", "object_state", "device_state", "local_mode"},
            )

        asyncio.run(run())

    def test_video_feed_requires_unlocked_ui(self):
        route = next(route for route in web_server.app.routes if getattr(route, "path", None) == "/video_feed")
        dependency_names = {item.call.__name__ for item in route.dependant.dependencies}
        self.assertIn("require_ui_unlock", dependency_names)

    def test_ui_lock_video_feed_requires_face_lock_enabled(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
            )
            with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=False):
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
            with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True), \
                 mock.patch.object(web_server.gate, "generate_frames", return_value=iter([b"frame"])):
                response = await web_server.ui_lock_video_feed(request)
            self.assertEqual(response.media_type, "multipart/x-mixed-replace; boundary=frame")

        asyncio.run(run())

    def test_initial_face_enroll_requires_bootstrap_flag(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/face/enroll"),
            )
            with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True), \
                 mock.patch.object(web_server, "ui_face_enrollment_enabled", return_value=False), \
                 mock.patch.object(web_server.face_lock, "enrollment_pending", return_value=False), \
                 mock.patch.object(web_server.face_lock, "is_enrolled", return_value=False), \
                 mock.patch.object(web_server.face_lock, "enroll_from_frames") as enroll:
                response = await web_server.face_enroll(request)
            enroll.assert_not_called()
            self.assertIn("disabled", response["error"])

        asyncio.run(run())

    def test_initial_face_enroll_accepts_bootstrap_flag(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                cookies={},
                url=SimpleNamespace(path="/face/enroll"),
            )
            with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True), \
                 mock.patch.object(web_server, "ui_face_enrollment_enabled", return_value=True), \
                 mock.patch.object(web_server, "_recent_camera_frames", return_value=[object()]), \
                 mock.patch.object(web_server.face_lock, "is_enrolled", return_value=False), \
                 mock.patch.object(web_server.face_lock, "enroll_from_frames", return_value=(True, "ok")) as enroll, \
                 mock.patch.object(web_server.face_lock, "clear_enrollment_request") as clear:
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
            with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True), \
                 mock.patch.object(web_server, "ui_face_enrollment_enabled", return_value=False), \
                 mock.patch.object(web_server.face_lock, "enrollment_pending", return_value=True), \
                 mock.patch.object(web_server, "_recent_camera_frames", return_value=[object()]), \
                 mock.patch.object(web_server.face_lock, "is_enrolled", return_value=False), \
                 mock.patch.object(web_server.face_lock, "enroll_from_frames", return_value=(True, "ok")) as enroll, \
                 mock.patch.object(web_server.face_lock, "clear_enrollment_request") as clear:
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
            with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True), \
                 mock.patch.object(web_server.face_lock, "is_enrolled", return_value=True), \
                 mock.patch.object(web_server, "_ui_unlocked", return_value=False), \
                 mock.patch.object(web_server.face_lock, "enroll_from_frames") as enroll:
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
            with mock.patch.object(web_server, "ui_face_lock_enabled", return_value=True), \
                 mock.patch.object(web_server.face_lock, "is_enrolled", return_value=True), \
                 mock.patch.object(web_server, "_ui_unlocked", return_value=True), \
                 mock.patch.object(web_server.face_lock, "enroll_from_frames") as enroll:
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
            self.assertIn(web_server.RESTRICTED_SESSION_COOKIE, response.headers.get("set-cookie", ""))

        asyncio.run(run())

    def test_restricted_confirmation_rejects_missing_or_stale_session(self):
        request = SimpleNamespace(
            client=SimpleNamespace(host="127.0.0.1"),
            cookies={},
        )
        with self.assertRaises(HTTPException) as ctx:
            web_server.require_restricted_confirmation(request)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_sensitive_routes_require_restricted_confirmation_dependency(self):
        sensitive_paths = {"/purge_other", "/emergency/brick", "/emergency/initialize"}
        for path in sensitive_paths:
            route = next(route for route in web_server.app.routes if getattr(route, "path", None) == path)
            dependency_names = {item.call.__name__ for item in route.dependant.dependencies}
            self.assertIn("require_restricted_confirmation", dependency_names)

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

    def test_emergency_initialize_requires_confirmation_phrase(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/emergency/initialize"),
            )
            with mock.patch.object(web_server.vault, "format_container") as init:
                response = await web_server.emergency_initialize(
                    request,
                    confirmation="INITIALIZE",
                )
            init.assert_not_called()
            self.assertIn("Confirmation required", response["error"])

        asyncio.run(run())

    def test_emergency_initialize_resets_container_and_bindings(self):
        async def run():
            request = SimpleNamespace(
                client=SimpleNamespace(host="127.0.0.1"),
                url=SimpleNamespace(path="/emergency/initialize"),
            )
            with mock.patch.object(web_server.vault, "format_container") as init, \
                 mock.patch.object(web_server.gate, "clear_references", return_value=(True, "ok")) as clear:
                response = await web_server.emergency_initialize(
                    request,
                    confirmation=web_server.INITIALIZE_CONTAINER_PHRASE,
                )
            init.assert_called_once_with(rotate_access_key=True)
            clear.assert_called_once_with()
            self.assertIn("initialized", response["status"])

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

    def test_download_response_uses_neutral_filename_and_state_header(self):
        response = web_server.create_file_response(b"payload", "source-name.txt", purge_applied=True)
        self.assertIn("retrieved_payload.bin", response.headers["content-disposition"])
        self.assertEqual(response.headers["x-local-state-updated"], "1")
        self.assertNotIn("source-name", str(response.headers).lower())


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
