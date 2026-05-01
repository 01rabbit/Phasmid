from pathlib import Path
import io
import os
import secrets
import time
import urllib.parse

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from .ai_gate import gate, get_gesture_sequence
from .audit import audit_event
from .config import (
    AUDIT_LOG_NAME,
    duress_mode_enabled,
    purge_confirmation_required,
    state_dir,
    ui_face_enrollment_enabled,
    ui_face_lock_enabled,
)
from .face_lock import face_lock
from .gv_core import GhostVault

app = FastAPI(title="Phantasm - Local Secure Interface")
templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
vault = GhostVault("vault.bin")
WEB_TOKEN = os.environ.get("PHANTASM_WEB_TOKEN") or secrets.token_urlsafe(32)
MAX_UPLOAD_BYTES = int(os.environ.get("PHANTASM_MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 20
FACE_SESSION_COOKIE = "phantasm_ui_session"
FACE_PREVIEW_COOKIE = "phantasm_face_preview"
FACE_FRAME_SAMPLES = 8
FACE_FRAME_DELAY_SECONDS = 0.10
FACE_PREVIEW_SECONDS = int(os.environ.get("PHANTASM_UI_FACE_PREVIEW_SECONDS", 30))
_rate_limit = {}
_face_preview_sessions = {}

ENTRY_TO_MODE = {
    "entry_1": "dummy",
    "entry_2": "secret",
}
LEGACY_PROFILE_TO_ENTRY = {
    "profile_a": "entry_1",
    "profile_b": "entry_2",
}
MODE_TO_ENTRY = {mode: entry for entry, mode in ENTRY_TO_MODE.items()}
ENTRY_LABELS = {
    "entry_1": "Entry 1",
    "entry_2": "Entry 2",
}
DESTRUCTIVE_CLEAR_PHRASE = "CLEAR LOCAL ENTRY"
INITIALIZE_CONTAINER_PHRASE = "INITIALIZE LOCAL CONTAINER"
EMERGENCY_BRICK_PHRASE = "BRICK LOCAL STATE"


def display_entry_label(entry_id):
    return ENTRY_LABELS.get(entry_id, "Entry")


def resolve_entry(entry_id):
    entry_id = LEGACY_PROFILE_TO_ENTRY.get(entry_id, entry_id)
    if entry_id not in ENTRY_TO_MODE:
        raise ValueError(f"unsupported entry id: {entry_id}")
    return ENTRY_TO_MODE[entry_id]


def mode_to_entry(mode):
    return MODE_TO_ENTRY.get(mode)


def _plain_form_value(value, default=""):
    return value if isinstance(value, str) else default


def _client_id(request):
    return request.client.host if request.client else "unknown"


def _face_session_token(request):
    return request.cookies.get(FACE_SESSION_COOKIE, "")


def _face_preview_token(request):
    return request.cookies.get(FACE_PREVIEW_COOKIE, "")


def _ui_unlocked(request):
    if not ui_face_lock_enabled():
        return True
    return face_lock.session_valid(_client_id(request), _face_session_token(request))


def _face_lock_status(request):
    if not ui_face_lock_enabled():
        return {"enabled": False, "enrolled": False, "unlocked": True, "failures": 0, "max_failures": 0}
    return face_lock.status(_client_id(request), _face_session_token(request))


def _face_enrollment_allowed():
    return ui_face_enrollment_enabled() or face_lock.enrollment_pending()


def require_ui_unlock(request: Request):
    if not _ui_unlocked(request):
        raise HTTPException(status_code=423, detail="ui locked")


def _start_face_preview_session(client_id):
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + FACE_PREVIEW_SECONDS
    _face_preview_sessions[token] = {"client_id": client_id, "expires_at": expires_at}
    return token, expires_at


def _face_preview_session(request):
    token = _face_preview_token(request)
    if not token:
        return None
    session = _face_preview_sessions.get(token)
    if not session:
        return None
    if session["client_id"] != _client_id(request):
        return None
    if session["expires_at"] <= time.time():
        _face_preview_sessions.pop(token, None)
        return None
    return session


def require_face_preview(request: Request):
    if not ui_face_lock_enabled():
        raise HTTPException(status_code=404, detail="face lock disabled")
    session = _face_preview_session(request)
    if session is None:
        raise HTTPException(status_code=423, detail="face preview locked")
    return session


def _generate_limited_face_preview(deadline):
    for chunk in gate.generate_frames():
        if time.time() >= deadline:
            break
        yield chunk


def _guard_page(request):
    if _ui_unlocked(request):
        return None
    return RedirectResponse(url="/ui-lock", status_code=303)


def _recent_camera_frames(count=FACE_FRAME_SAMPLES, delay=FACE_FRAME_DELAY_SECONDS):
    frames = []
    for _ in range(count):
        with gate.lock:
            frame = None if gate.latest_frame is None else gate.latest_frame.copy()
        if frame is not None:
            frames.append(frame)
        time.sleep(delay)
    return frames


def require_web_token(x_phantasm_token: str = Header(default="")):
    if not secrets.compare_digest(x_phantasm_token, WEB_TOKEN):
        raise HTTPException(status_code=403, detail="invalid web token")


def enforce_rate_limit(request: Request):
    client = request.client.host if request.client else "unknown"
    key = (client, request.url.path)
    now = time.time()
    bucket = [timestamp for timestamp in _rate_limit.get(key, []) if now - timestamp < RATE_LIMIT_WINDOW]
    if len(bucket) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    bucket.append(now)
    _rate_limit[key] = bucket


async def read_limited_upload(file: UploadFile):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="upload too large")
    return data


def _template_context(request: Request, active="home", **extra):
    context = {
        "request": request,
        "active": active,
        "web_token": WEB_TOKEN,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "purge_confirmation_required": purge_confirmation_required(),
        "duress_mode_enabled": duress_mode_enabled(),
        "face_enrollment_enabled": _face_enrollment_allowed(),
        "face_lock": _face_lock_status(request),
        "destructive_clear_phrase": DESTRUCTIVE_CLEAR_PHRASE,
        "initialize_container_phrase": INITIALIZE_CONTAINER_PHRASE,
        "emergency_brick_phrase": EMERGENCY_BRICK_PHRASE,
        "entries": [
            {"id": entry_id, "label": label}
            for entry_id, label in ENTRY_LABELS.items()
        ],
    }
    context.update(extra)
    return context


def _raw_gate_status():
    return gate.get_status()


def neutral_status():
    raw = _raw_gate_status()
    matched_mode = raw.get("matched_mode")
    with gate.lock:
        camera_ready = gate.latest_frame is not None

    if matched_mode == gate.MATCH_AMBIGUOUS:
        object_state = "ambiguous"
    elif matched_mode in gate.AUTH_TOKENS:
        object_state = "matched"
    elif raw.get("object_detected"):
        object_state = "detected"
    else:
        object_state = "none"

    return {
        "camera_ready": camera_ready,
        "object_state": object_state,
        "device_state": "ready",
        "local_mode": True,
    }


def entry_management_status():
    raw = _raw_gate_status()
    registered = raw.get("registered_modes", {})
    current_entry = mode_to_entry(raw.get("matched_mode"))
    return {
        "entries": [
            {
                "id": entry_id,
                "label": label,
                "bound": bool(registered.get(ENTRY_TO_MODE[entry_id])),
                "matched": entry_id == current_entry,
            }
            for entry_id, label in ENTRY_LABELS.items()
        ],
        "object_state": neutral_status()["object_state"],
    }


def _first_unbound_entry():
    registered = _raw_gate_status().get("registered_modes", {})
    for entry_id, mode in ENTRY_TO_MODE.items():
        if not registered.get(mode):
            return entry_id
    return None


def _matched_entry():
    matched_mode = _raw_gate_status().get("matched_mode")
    if matched_mode in gate.AUTH_TOKENS:
        return mode_to_entry(matched_mode)
    return None


def _select_entry_for_store(entry_hint=None, overwrite=False):
    matched_entry = _matched_entry()
    if matched_entry:
        return matched_entry, False

    free_entry = _first_unbound_entry()
    if free_entry:
        return free_entry, True

    if overwrite and entry_hint in ENTRY_TO_MODE:
        return entry_hint, True

    return None, False


def _capture_entry_binding(mode):
    success, message = gate.capture_reference(mode)
    if not success:
        return False, "Object binding failed. Retry capture."
    return True, message


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    guard = _guard_page(request)
    if guard:
        return guard
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context=_template_context(request, active="home"),
    )


@app.get("/store", response_class=HTMLResponse)
async def store_page(request: Request):
    guard = _guard_page(request)
    if guard:
        return guard
    return templates.TemplateResponse(
        request=request,
        name="store.html",
        context=_template_context(request, active="store"),
    )


@app.get("/retrieve", response_class=HTMLResponse)
async def retrieve_page(request: Request):
    guard = _guard_page(request)
    if guard:
        return guard
    return templates.TemplateResponse(
        request=request,
        name="retrieve.html",
        context=_template_context(request, active="retrieve"),
    )


@app.get("/maintenance", response_class=HTMLResponse)
async def maintenance_page(request: Request):
    guard = _guard_page(request)
    if guard:
        return guard
    return templates.TemplateResponse(
        request=request,
        name="maintenance.html",
        context=_template_context(
            request,
            active="maintenance",
            audit_enabled=os.environ.get("PHANTASM_AUDIT", "0"),
            state_path=state_dir(),
        ),
    )


@app.get("/maintenance/entries", response_class=HTMLResponse)
async def entry_management_page(request: Request):
    guard = _guard_page(request)
    if guard:
        return guard
    return templates.TemplateResponse(
        request=request,
        name="entry_management.html",
        context=_template_context(
            request,
            active="maintenance",
            entry_status=entry_management_status(),
        ),
    )


@app.get("/emergency", response_class=HTMLResponse)
async def emergency_page(request: Request):
    guard = _guard_page(request)
    if guard:
        return guard
    return templates.TemplateResponse(
        request=request,
        name="emergency.html",
        context=_template_context(request, active="maintenance"),
    )


@app.get("/ui-lock", response_class=HTMLResponse)
async def ui_lock_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="ui_lock.html",
        context=_template_context(request, active="lock"),
    )


@app.get("/video_feed", dependencies=[Depends(require_ui_unlock)])
async def video_feed():
    return StreamingResponse(
        gate.generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.post("/ui-lock/preview", dependencies=[Depends(require_web_token)])
async def ui_lock_preview(request: Request):
    enforce_rate_limit(request)
    if not ui_face_lock_enabled():
        return {"error": "Face UI lock is disabled."}
    if not face_lock.is_enrolled() and not _face_enrollment_allowed():
        return {"error": "Face enrollment is disabled for this session."}
    token, expires_at = _start_face_preview_session(_client_id(request))
    response = JSONResponse({"status": "Camera preview ready.", "seconds": FACE_PREVIEW_SECONDS})
    response.set_cookie(
        FACE_PREVIEW_COOKIE,
        token,
        max_age=FACE_PREVIEW_SECONDS,
        httponly=True,
        samesite="strict",
    )
    audit_event("ui_face_preview_started", source="web", expires_at=int(expires_at))
    return response


@app.get("/ui-lock/video_feed")
async def ui_lock_video_feed(request: Request):
    session = require_face_preview(request)
    return StreamingResponse(
        _generate_limited_face_preview(session["expires_at"]),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/status")
async def status(request: Request):
    data = neutral_status()
    face_status = _face_lock_status(request)
    if face_status["enabled"] and not face_status["unlocked"]:
        data["device_state"] = "locked"
        data["camera_ready"] = False
        data["object_state"] = "none"
    data["ui_lock"] = face_status
    return data


@app.post("/face/enroll", dependencies=[Depends(require_web_token)])
async def face_enroll(request: Request):
    enforce_rate_limit(request)
    if not ui_face_lock_enabled():
        return {"error": "Face UI lock is disabled."}
    if not face_lock.is_enrolled() and not _face_enrollment_allowed():
        return {"error": "Face enrollment is disabled for this session."}
    if face_lock.is_enrolled() and not _ui_unlocked(request):
        return {"error": "UI must be unlocked before replacing the face lock."}
    success, message = face_lock.enroll_from_frames(_recent_camera_frames())
    if success:
        face_lock.clear_enrollment_request()
        audit_event("ui_face_lock_enrolled", source="web")
        return {"status": message}
    return {"error": message}


@app.post("/face/verify", dependencies=[Depends(require_web_token)])
async def face_verify(request: Request):
    enforce_rate_limit(request)
    if not ui_face_lock_enabled():
        return {"error": "Face UI lock is disabled."}
    client_id = _client_id(request)
    success, message = face_lock.verify_from_frames(_recent_camera_frames(), client_id)
    if not success:
        audit_event("ui_face_lock_failed", source="web")
        return {"error": message}

    token = secrets.token_urlsafe(32)
    face_lock.create_session(client_id, token)
    audit_event("ui_face_lock_unlocked", source="web")
    response = JSONResponse({"status": "UI unlocked."})
    response.set_cookie(
        FACE_SESSION_COOKIE,
        token,
        max_age=int(os.environ.get("PHANTASM_UI_FACE_SESSION_SECONDS", face_lock.SESSION_TTL_SECONDS)),
        httponly=True,
        samesite="strict",
    )
    return response


@app.post("/face/lock", dependencies=[Depends(require_web_token)])
async def face_lock_session(request: Request):
    face_lock.clear_session(_face_session_token(request))
    response = JSONResponse({"status": "UI locked."})
    response.delete_cookie(FACE_SESSION_COOKIE)
    return response


@app.get("/maintenance/entry_status", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def entry_status(request: Request):
    enforce_rate_limit(request)
    return entry_management_status()


@app.post("/register_key", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def register_key(
    request: Request,
    entry_hint: str = Form(default=""),
    replace: bool = Form(False),
):
    enforce_rate_limit(request)
    entry_id = entry_hint if entry_hint in ENTRY_TO_MODE else _matched_entry() or _first_unbound_entry()
    if entry_id is None:
        return {
            "error": "No open local entry is available.",
            "overwrite_required": True,
            "entries": list(ENTRY_LABELS.values()),
        }

    mode = resolve_entry(entry_id)
    if entry_hint in ENTRY_TO_MODE and not replace and _raw_gate_status()["registered_modes"].get(mode):
        return {"error": "Entry already has a bound object. Confirm replacement first."}

    success, message = _capture_entry_binding(mode)
    if success:
        audit_event("image_key_registered", entry=display_entry_label(entry_id), source="web")
        return {"status": "Object bound to protected entry.", "entry_label": display_entry_label(entry_id)}
    return {"error": message}


@app.post("/store", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def store(
    request: Request,
    file: UploadFile = File(...),
    password: str = Form(...),
    purge_password: str = Form(default=""),
    local_note_label: str = Form(default=""),
    entry_hint: str = Form(default=""),
    overwrite: bool = Form(False),
):
    enforce_rate_limit(request)
    data = await read_limited_upload(file)
    orig_filename = file.filename

    try:
        if not password:
            return {"error": "Access password must not be empty."}
        if purge_password and password == purge_password:
            return {"error": "Access and destructive passwords must be different."}

        entry_id, needs_capture = _select_entry_for_store(entry_hint=entry_hint, overwrite=overwrite)
        if entry_id is None:
            return {
                "error": "No open local entry is available. Confirm replacement to continue.",
                "overwrite_required": True,
                "entries": [
                    {"id": item_id, "label": label}
                    for item_id, label in ENTRY_LABELS.items()
                ],
            }

        mode = resolve_entry(entry_id)
        if needs_capture or overwrite:
            success, message = _capture_entry_binding(mode)
            if not success:
                return {"error": message}

        vault.store(
            password,
            data,
            gate.sequence_for_mode(mode),
            filename=orig_filename,
            mode=mode,
            purge_password=purge_password or None,
        )
        audit_event(
            "payload_stored",
            entry=display_entry_label(entry_id),
            filename=orig_filename,
            bytes=len(data),
            label_present=bool(local_note_label),
            source="web",
        )
        return {"status": "Protected entry saved.", "entry_label": display_entry_label(entry_id)}
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/retrieve", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def retrieve(request: Request, password: str = Form(...)):
    enforce_rate_limit(request)
    auth_sequence = get_gesture_sequence(length=1)
    if gate.last_match_mode == gate.MATCH_AMBIGUOUS:
        return {"error": "Ambiguous object match."}
    if auth_sequence[0] == gate.MATCH_NONE:
        return {"error": "No valid entry found."}

    for mode in ("dummy", "secret"):
        result, filename, password_role = vault.retrieve_with_policy(password, auth_sequence, mode=mode)
        if result is None:
            continue

        entry_id = mode_to_entry(mode)
        audit_event(
            "payload_retrieved",
            entry=display_entry_label(entry_id),
            filename=filename,
            bytes=len(result),
            source="web",
        )
        purge_applied = _purge_for_password_role(mode, password_role, source="web")
        if not purge_applied:
            purge_applied = _maybe_auto_purge(mode, source="web")
        return create_file_response(
            result,
            filename or "protected-entry.bin",
            purge_applied=purge_applied,
        )

    audit_event("retrieve_failed", source="web")
    return {"error": "No valid entry found."}


@app.post("/purge_other", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def purge_other(
    request: Request,
    accessed_entry: str = Form(default=""),
    accessed_profile: str = Form(default=""),
    confirmation: str = Form(...),
):
    enforce_rate_limit(request)
    entry_id = _plain_form_value(accessed_entry) or LEGACY_PROFILE_TO_ENTRY.get(
        _plain_form_value(accessed_profile),
        _plain_form_value(accessed_profile),
    )
    mode = resolve_entry(entry_id)
    if confirmation != DESTRUCTIVE_CLEAR_PHRASE:
        return {"error": f"Confirmation required: {DESTRUCTIVE_CLEAR_PHRASE}"}

    vault.purge_other_mode(mode)
    audit_event("alternate_entry_cleared", accessed_entry=display_entry_label(entry_id), source="web")
    return {"status": "Unmatched local entry cleared."}


@app.post("/emergency/brick", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def emergency_brick(request: Request, confirmation: str = Form(...)):
    enforce_rate_limit(request)
    if confirmation != EMERGENCY_BRICK_PHRASE:
        return {"error": f"Confirmation required: {EMERGENCY_BRICK_PHRASE}"}
    vault.silent_brick()
    audit_event("container_bricked", source="web")
    return {"status": "Emergency brick completed. Close this session."}


@app.post("/emergency/initialize", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def emergency_initialize(request: Request, confirmation: str = Form(...)):
    enforce_rate_limit(request)
    if confirmation != INITIALIZE_CONTAINER_PHRASE:
        return {"error": f"Confirmation required: {INITIALIZE_CONTAINER_PHRASE}"}
    vault.format_container(rotate_access_key=True)
    success, message = gate.clear_references()
    if not success:
        return {"error": message}
    audit_event("container_initialized", source="web")
    return {"status": "Local container initialized. Protected entries are empty."}


@app.post("/maintenance/rotate_token", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def rotate_token(request: Request):
    enforce_rate_limit(request)
    global WEB_TOKEN
    WEB_TOKEN = secrets.token_urlsafe(32)
    audit_event("web_token_rotated", source="web")
    return {"status": "Session token rotated.", "web_token": WEB_TOKEN}


@app.post("/maintenance/reset_session", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def reset_session(request: Request):
    enforce_rate_limit(request)
    _rate_limit.clear()
    return {"status": "Local session counters reset."}


@app.get("/maintenance/diagnostics", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def diagnostics(request: Request):
    enforce_rate_limit(request)
    status_data = neutral_status()
    return {
        "device_state": status_data["device_state"],
        "camera_ready": status_data["camera_ready"],
        "object_state": status_data["object_state"],
        "local_mode": status_data["local_mode"],
        "state_directory": state_dir(),
        "audit_enabled": os.environ.get("PHANTASM_AUDIT", "0").lower() not in {"0", "false", "off", "no"},
        "upload_limit_bytes": MAX_UPLOAD_BYTES,
    }


@app.get("/maintenance/logs", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)])
async def export_logs(request: Request):
    enforce_rate_limit(request)
    path = Path(state_dir()) / AUDIT_LOG_NAME
    if not path.exists():
        return JSONResponse({"error": "No local event log is available."}, status_code=404)
    data = path.read_bytes()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/jsonl",
        headers={"Content-Disposition": "attachment; filename=phantasm-events.jsonl"},
    )


def _maybe_auto_purge(accessed_mode, source):
    reason = None
    if duress_mode_enabled() and accessed_mode == "dummy":
        reason = "duress_dummy_access"
    elif not purge_confirmation_required():
        reason = "confirmation_disabled"

    if reason is None:
        return False

    vault.purge_other_mode(accessed_mode)
    audit_event(
        "alternate_entry_cleared",
        accessed_entry=display_entry_label(mode_to_entry(accessed_mode)),
        source=source,
        reason=reason,
    )
    return True


def _purge_for_password_role(accessed_mode, password_role, source):
    if password_role != GhostVault.PURGE_ROLE:
        return False
    vault.purge_other_mode(accessed_mode)
    audit_event(
        "alternate_entry_cleared",
        accessed_entry=display_entry_label(mode_to_entry(accessed_mode)),
        source=source,
        reason="destructive_password",
    )
    return True


def create_file_response(content, filename, purge_applied=False):
    safe_filename = urllib.parse.quote(filename)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
            "X-Filename": safe_filename,
            "X-Purge-Applied": "1" if purge_applied else "0",
        },
    )


if __name__ == "__main__":
    host = os.environ.get("PHANTASM_HOST", "127.0.0.1")
    port = int(os.environ.get("PHANTASM_PORT", "8000"))
    print(f"[WEB] Starting on http://{host}:{port}")
    print("[WEB] Mutating requests require X-Phantasm-Token from the served UI.")
    uvicorn_run = __import__("uvicorn").run
    uvicorn_run(app, host=host, port=port)
