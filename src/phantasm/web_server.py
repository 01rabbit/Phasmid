import io
import os
import secrets
import time
import urllib.parse
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates

from . import strings as text
from .ai_gate import gate, get_gesture_sequence
from .attempt_limiter import AttemptLimiter
from .audit import audit_event
from .capabilities import Capability, active_policy, capability_enabled
from .config import (
    AUDIT_LOG_NAME,
    duress_mode_enabled,
    field_mode_enabled,
    purge_confirmation_required,
    state_dir,
    ui_face_enrollment_enabled,
    ui_face_lock_enabled,
)
from .crypto_boundary import ensure_crypto_self_tests
from .face_lock import face_lock
from .gv_core import GhostVault
from .metadata import metadata_risk_report, scrub_metadata
from .passphrase_policy import check_store_passphrases
from .restricted_actions import (
    DESTRUCTIVE_CLEAR_PHRASE,
    EMERGENCY_BRICK_PHRASE,
    INITIALIZE_CONTAINER_PHRASE,
    OVERWRITE_CONFIRMATION_PHRASE,
    RESTRICTED_ACTION_POLICIES,
    RESTRICTED_CONFIRMATION_PHRASE,
    RestrictedActionRejected,
    evaluate_restricted_action,
)

app = FastAPI(title="Phantasm - Local Secure Interface")


@app.on_event("startup")
async def startup_self_tests():
    ensure_crypto_self_tests()


templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
vault = GhostVault("vault.bin")
WEB_TOKEN = os.environ.get("PHANTASM_WEB_TOKEN") or secrets.token_urlsafe(32)
MAX_UPLOAD_BYTES = int(os.environ.get("PHANTASM_MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 20
FACE_SESSION_COOKIE = "phantasm_ui_session"
RESTRICTED_SESSION_COOKIE = "phantasm_restricted_session"
FACE_FRAME_SAMPLES = 8
FACE_FRAME_DELAY_SECONDS = 0.10
RESTRICTED_SESSION_TTL_SECONDS = int(
    os.environ.get("PHANTASM_RESTRICTED_SESSION_SECONDS", 120)
)
_restricted_sessions = {}
_access_attempts = AttemptLimiter()

ENTRY_TO_MODE = {
    "entry_1": gate.MODES[0],
    "entry_2": gate.MODES[1],
}
LEGACY_SELECTOR_TO_ENTRY = {
    "prof" + "ile_a": "entry_1",
    "prof" + "ile_b": "entry_2",
}
MODE_TO_ENTRY = {mode: entry for entry, mode in ENTRY_TO_MODE.items()}
ENTRY_LABELS = {
    "entry_1": "Entry 1",
    "entry_2": "Entry 2",
}
SECURITY_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "base-uri 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def _apply_security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        response.headers[name] = value
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    return _apply_security_headers(response)


def display_entry_label(entry_id):
    return ENTRY_LABELS.get(entry_id, "Entry")


def resolve_entry(entry_id):
    entry_id = LEGACY_SELECTOR_TO_ENTRY.get(entry_id, entry_id)
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


def _restricted_session_token(request):
    return request.cookies.get(RESTRICTED_SESSION_COOKIE, "")


def _ui_unlocked(request):
    if not ui_face_lock_enabled():
        return True
    return face_lock.session_valid(_client_id(request), _face_session_token(request))


def _face_lock_status(request):
    if not ui_face_lock_enabled():
        return {
            "enabled": False,
            "enrolled": False,
            "unlocked": True,
            "failures": 0,
            "max_failures": 0,
        }
    return face_lock.status(_client_id(request), _face_session_token(request))


def _face_enrollment_allowed():
    if not face_lock.is_enrolled():
        return True
    return ui_face_enrollment_enabled() or face_lock.enrollment_pending()


def require_ui_unlock(request: Request):
    if not _ui_unlocked(request):
        raise HTTPException(status_code=423, detail=text.UI_LOCKED)


def _create_restricted_session(client_id):
    token = secrets.token_urlsafe(32)
    _restricted_sessions[token] = {
        "client_id": client_id,
        "expires_at": time.time() + RESTRICTED_SESSION_TTL_SECONDS,
    }
    return token


def _restricted_session_valid(request):
    token = _restricted_session_token(request)
    if not token:
        return False
    session = _restricted_sessions.get(token)
    if not session:
        return False
    if session["client_id"] != _client_id(request):
        return False
    if session["expires_at"] <= time.time():
        _restricted_sessions.pop(token, None)
        return False
    return True


def require_restricted_confirmation(request: Request):
    if not _restricted_session_valid(request):
        raise HTTPException(
            status_code=403, detail=text.RESTRICTED_CONFIRMATION_REQUIRED
        )


def _require_restricted_when_field_mode(request):
    if field_mode_enabled() and not _restricted_session_valid(request):
        raise HTTPException(
            status_code=403, detail=text.RESTRICTED_CONFIRMATION_REQUIRED
        )


def require_capability(capability: Capability):
    if not capability_enabled(capability):
        raise HTTPException(status_code=403, detail=text.OPERATION_UNAVAILABLE)


def require_restricted_action(action_id, request, confirmation=""):
    policy = RESTRICTED_ACTION_POLICIES[action_id]
    try:
        evaluate_restricted_action(
            policy,
            capability_allowed=capability_enabled(policy.capability),
            restricted_confirmed=_restricted_session_valid(request),
            confirmation=confirmation,
        )
    except RestrictedActionRejected as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc


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
        raise HTTPException(status_code=403, detail=text.INVALID_WEB_TOKEN)
_rate_limit: dict[str, list[float]] = {}

def enforce_rate_limit(request: Request):
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{request.url.path}"
    now = time.time()
    bucket = [
        timestamp
        for timestamp in _rate_limit.get(key, [])
        if now - timestamp < RATE_LIMIT_WINDOW
    ]
    if len(bucket) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail=text.RATE_LIMIT_EXCEEDED)
    bucket.append(now)
    _rate_limit[key] = bucket



async def read_limited_upload(file: UploadFile):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=text.UPLOAD_TOO_LARGE)
    return data


def _template_context(request: Request, active="home", **extra):
    restricted_confirmed = _restricted_session_valid(request)
    context = {
        "request": request,
        "active": active,
        "web_token": WEB_TOKEN,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "purge_confirmation_required": purge_confirmation_required(),
        "duress_mode_enabled": duress_mode_enabled(),
        "field_mode": field_mode_enabled(),
        "deployment_mode": active_policy().name,
        "restricted_confirmed": restricted_confirmed,
        "face_enrollment_enabled": _face_enrollment_allowed(),
        "face_lock": _face_lock_status(request),
        "destructive_clear_phrase": DESTRUCTIVE_CLEAR_PHRASE,
        "initialize_container_phrase": INITIALIZE_CONTAINER_PHRASE,
        "emergency_brick_phrase": EMERGENCY_BRICK_PHRASE,
        "restricted_confirmation_phrase": RESTRICTED_CONFIRMATION_PHRASE,
        "overwrite_confirmation_phrase": OVERWRITE_CONFIRMATION_PHRASE,
        "entries": [
            {"id": entry_id, "label": label} for entry_id, label in ENTRY_LABELS.items()
        ],
    }
    context.update(extra)
    return context


def _deceptive_path(original_path: str):
    """Provides a cover-story path when field mode is enabled."""
    if field_mode_enabled() and original_path:
        return "/usr/lib/firmware/updates/recovery_blob.bin"
    return original_path


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
    restricted_confirmed = _restricted_session_valid(request)
    return templates.TemplateResponse(
        request=request,
        name="maintenance.html",
        context=_template_context(
            request,
            active="maintenance",
            restricted_confirmed=restricted_confirmed,
            audit_enabled=os.environ.get("PHANTASM_AUDIT", "0"),
            state_path=(
                state_dir()
                if (not field_mode_enabled() or restricted_confirmed)
                else ""
            ),
        ),
    )


@app.get("/maintenance/entries", response_class=HTMLResponse)
async def entry_management_page(request: Request):
    guard = _guard_page(request)
    if guard:
        return guard
    restricted_confirmed = _restricted_session_valid(request)
    return templates.TemplateResponse(
        request=request,
        name="entry_management.html",
        context=_template_context(
            request,
            active="maintenance",
            restricted_confirmed=restricted_confirmed,
        ),
    )


@app.get("/emergency", response_class=HTMLResponse)
async def emergency_page(request: Request):
    guard = _guard_page(request)
    if guard:
        return guard
    restricted_confirmed = _restricted_session_valid(request)
    return templates.TemplateResponse(
        request=request,
        name="emergency.html",
        context=_template_context(
            request, active="maintenance", restricted_confirmed=restricted_confirmed
        ),
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


@app.get("/ui-lock/video_feed")
async def ui_lock_video_feed(request: Request):
    if not ui_face_lock_enabled():
        raise HTTPException(status_code=404, detail="face lock disabled")
    return StreamingResponse(
        gate.generate_frames(),
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
    return data


@app.post("/face/enroll", dependencies=[Depends(require_web_token)])
async def face_enroll(request: Request):
    enforce_rate_limit(request)
    require_capability(Capability.FACE_ENROLL)
    if not ui_face_lock_enabled():
        return {"error": "Face UI lock is disabled."}
    if not face_lock.is_enrolled() and not _face_enrollment_allowed():
        return {"error": "Face enrollment is disabled for this session."}
    if face_lock.is_enrolled() and not _ui_unlocked(request):
        return {"error": "UI must be unlocked before replacing the face lock."}
    if face_lock.is_enrolled() and not _restricted_session_valid(request):
        return {
            "error": "Restricted confirmation required. Please confirm local control and retry."
        }
    success, message = face_lock.enroll_from_frames(_recent_camera_frames())
    if success:
        face_lock.clear_enrollment_request()
        audit_event("ui_face_lock_enrolled", source="web")
        return {"status": message}
    return {"error": message}


@app.post("/face/verify", dependencies=[Depends(require_web_token)])
async def face_verify(request: Request):
    enforce_rate_limit(request)
    require_capability(Capability.FACE_VERIFY)
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
    response = JSONResponse({"status": text.UI_UNLOCKED})
    response.set_cookie(
        FACE_SESSION_COOKIE,
        token,
        max_age=int(
            os.environ.get(
                "PHANTASM_UI_FACE_SESSION_SECONDS", face_lock.SESSION_TTL_SECONDS
            )
        ),
        httponly=True,
        samesite="strict",
    )
    return response


@app.post("/face/lock", dependencies=[Depends(require_web_token)])
async def face_lock_session(request: Request):
    face_lock.clear_session(_face_session_token(request))
    _restricted_sessions.pop(_restricted_session_token(request), None)
    response = JSONResponse({"status": text.UI_LOCKED_FEEDBACK})
    response.delete_cookie(FACE_SESSION_COOKIE)
    response.delete_cookie(RESTRICTED_SESSION_COOKIE)
    return response


@app.get(
    "/maintenance/entry_status",
    dependencies=[
        Depends(require_web_token),
        Depends(require_ui_unlock),
        Depends(require_restricted_confirmation),
    ],
)
async def entry_status(request: Request, entry_id: str = "entry_1"):
    enforce_rate_limit(request)
    require_capability(Capability.ENTRY_MAINTENANCE)
    if entry_id not in ENTRY_TO_MODE:
        return {"error": "Unknown local entry."}
    status_data = entry_management_status()
    selected = next(item for item in status_data["entries"] if item["id"] == entry_id)
    return {
        "label": selected["label"],
        "bound": selected["bound"],
        "matched": selected["matched"],
    }


@app.post(
    "/restricted/confirm",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def restricted_confirm(request: Request, confirmation: str = Form(...)):
    enforce_rate_limit(request)
    if confirmation != RESTRICTED_CONFIRMATION_PHRASE:
        return {"error": text.CONFIRMATION_REJECTED_DISPLAY}
    token = _create_restricted_session(_client_id(request))
    response = JSONResponse(
        {
            "status": text.RESTRICTED_CONFIRMATION_ACCEPTED,
            "expires_in": RESTRICTED_SESSION_TTL_SECONDS,
        }
    )
    response.set_cookie(
        RESTRICTED_SESSION_COOKIE,
        token,
        max_age=RESTRICTED_SESSION_TTL_SECONDS,
        httponly=True,
        samesite="strict",
    )
    audit_event("restricted_confirmation_accepted", source="web")
    return response


@app.post(
    "/register_key",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def register_key(
    request: Request,
    entry_hint: str = Form(default=""),
    replace: bool = Form(False),
):
    enforce_rate_limit(request)
    if replace and not _restricted_session_valid(request):
        return {"error": text.RESTRICTED_CONFIRMATION_REQUIRED_UI}
    entry_id = (
        entry_hint
        if entry_hint in ENTRY_TO_MODE
        else _matched_entry() or _first_unbound_entry()
    )
    if entry_id is None:
        return {
            "error": text.NO_OPEN_LOCAL_ENTRY,
            "overwrite_required": True,
            "entries": list(ENTRY_LABELS.values()),
        }

    mode = resolve_entry(entry_id)
    if (
        entry_hint in ENTRY_TO_MODE
        and not replace
        and _raw_gate_status()["registered_modes"].get(mode)
    ):
        return {"error": text.ENTRY_ALREADY_BOUND}

    success, message = _capture_entry_binding(mode)
    if success:
        audit_event("image_key_registered", entry="local_entry", source="web")
        return {
            "status": text.OBJECT_BOUND_TO_ENTRY,
            "entry_state": "updated" if replace else "created",
        }
    return {"error": message}


@app.post(
    "/store", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)]
)
async def store(
    request: Request,
    file: UploadFile = File(...),
    password: str = Form(...),
    restricted_recovery_password: str = Form(default=""),
    local_note_label: str = Form(default=""),
    entry_hint: str = Form(default=""),
    overwrite: bool = Form(False),
    overwrite_confirmation: str = Form(default=""),
):
    enforce_rate_limit(request)
    data = await read_limited_upload(file)
    orig_filename = file.filename

    try:
        if not password:
            return {"error": text.ACCESS_PASSWORD_REQUIRED}
        passphrase_check = check_store_passphrases(
            password,
            restricted_recovery_password,
        )
        if not passphrase_check.ok:
            return {"error": passphrase_check.message}
        if overwrite and overwrite_confirmation != OVERWRITE_CONFIRMATION_PHRASE:
            return {"error": text.REPLACEMENT_CONFIRMATION_REQUIRED}
        if overwrite and not _restricted_session_valid(request):
            return {"error": text.RESTRICTED_CONFIRMATION_REQUIRED_UI}

        entry_id, needs_capture = _select_entry_for_store(
            entry_hint=entry_hint, overwrite=overwrite
        )
        if entry_id is None:
            return {
                "error": text.NO_OPEN_LOCAL_ENTRY_WITH_REPLACEMENT,
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
            restricted_recovery_password=restricted_recovery_password or None,
        )
        audit_event(
            "payload_stored",
            entry="local_entry",
            filename=orig_filename,
            bytes=len(data),
            label_present=bool(local_note_label),
            source="web",
        )
        entry_state = (
            "replaced" if overwrite else "created" if needs_capture else "updated"
        )
        return {
            "success": True,
            "message": text.PROTECTED_ENTRY_SAVED,
            "entry_state": entry_state,
        }
    except Exception:
        return {"error": text.STORE_OPERATION_FAILED}


@app.post(
    "/metadata/check",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def metadata_check(request: Request, file: UploadFile = File(...)):
    enforce_rate_limit(request)
    require_capability(Capability.METADATA_CHECK)
    data = await read_limited_upload(file)
    return metadata_risk_report(file.filename, data)


@app.post(
    "/metadata/scrub",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def metadata_scrub(request: Request, file: UploadFile = File(...)):
    enforce_rate_limit(request)
    require_capability(Capability.METADATA_REDUCE)
    data = await read_limited_upload(file)
    result = scrub_metadata(file.filename, data)
    if not result["success"]:
        return JSONResponse(
            {"error": result["message"], "limitation": result["limitation"]},
            status_code=422,
        )
    safe_filename = urllib.parse.quote("metadata_reduced_payload.bin")
    return StreamingResponse(
        io.BytesIO(result["data"]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
            "X-Result-Filename": safe_filename,
        },
    )


@app.post(
    "/retrieve", dependencies=[Depends(require_web_token), Depends(require_ui_unlock)]
)
async def retrieve(request: Request, password: str = Form(...)):
    enforce_rate_limit(request)
    attempt_scope = f"web:{_client_id(request)}"
    if not _access_attempts.check(attempt_scope).allowed:
        return {"error": text.ACCESS_TEMPORARILY_UNAVAILABLE}
    auth_sequence = get_gesture_sequence(length=1)
    if gate.last_match_mode == gate.MATCH_AMBIGUOUS:
        _access_attempts.record_failure(attempt_scope)
        return {"error": text.AMBIGUOUS_OBJECT_MATCH}
    if auth_sequence[0] == gate.MATCH_NONE:
        _access_attempts.record_failure(attempt_scope)
        return {"error": text.NO_VALID_ENTRY_FOUND}

    for mode in gate.MODES:
        result, filename, password_role = vault.retrieve_with_policy(
            password, auth_sequence, mode=mode
        )
        if result is None:
            continue

        audit_event(
            "payload_retrieved",
            entry="local_entry",
            filename=filename,
            bytes=len(result),
            source="web",
        )
        purge_applied = _purge_for_password_role(mode, password_role, source="web")
        if result is not None:
            # Release camera to save power and heat after successful retrieval
            gate.close()
        _access_attempts.record_success(attempt_scope)
        if not purge_applied:
            purge_applied = _maybe_auto_purge(mode, source="web")
        return create_file_response(
            result,
            filename or "protected-entry.bin",
            purge_applied=purge_applied,
        )

    audit_event("retrieve_failed", source="web")
    _access_attempts.record_failure(attempt_scope)
    return {"error": text.NO_VALID_ENTRY_FOUND}


@app.post(
    "/purge_other",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def purge_other(
    request: Request,
    accessed_entry: str = Form(default=""),
    legacy_selector: str = Form(default=""),
    confirmation: str = Form(...),
):
    enforce_rate_limit(request)
    require_restricted_action("clear_unmatched_entry", request, confirmation)
    entry_id = _plain_form_value(accessed_entry) or LEGACY_SELECTOR_TO_ENTRY.get(
        _plain_form_value(legacy_selector),
        _plain_form_value(legacy_selector),
    )
    mode = resolve_entry(entry_id)
    vault.purge_other_mode(mode)
    audit_event("restricted_local_update", accessed_entry="local_entry", source="web")
    return {"status": text.UNMATCHED_ENTRY_CLEARED}


@app.post(
    "/emergency/brick",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def emergency_brick(request: Request, confirmation: str = Form(...)):
    enforce_rate_limit(request)
    require_restricted_action("clear_local_access_path", request, confirmation)
    vault.silent_brick()
    audit_event("access_path_cleared", source="web")
    return {"status": text.LOCAL_ACCESS_PATH_CLEARED}


@app.post(
    "/emergency/initialize",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def emergency_initialize(request: Request, confirmation: str = Form(...)):
    enforce_rate_limit(request)
    require_restricted_action("initialize_container", request, confirmation)
    vault.format_container(rotate_access_key=True)
    success, message = gate.clear_references()
    if not success:
        return {"error": message}
    audit_event("container_reinitialized", source="web")
    return {"status": text.CONTAINER_INITIALIZED}


@app.post("/emergency/panic", dependencies=[Depends(require_web_token)])
async def web_panic_trigger(request: Request, secret_trigger: str = Form(...)):
    """Hidden endpoint for rapid local state destruction."""
    enforce_rate_limit(request)
    try:
        require_restricted_action("rapid_local_clear", request, secret_trigger)
    except HTTPException:
        raise HTTPException(status_code=404) from None
    vault.silent_brick()
    audit_event("access_path_cleared", source="web_panic")
    return {"status": text.CRITICAL_STATE_CLEARED}


@app.post(
    "/maintenance/rotate_token",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def rotate_token(request: Request):
    enforce_rate_limit(request)
    require_capability(Capability.TOKEN_ROTATION)
    _require_restricted_when_field_mode(request)
    global WEB_TOKEN
    WEB_TOKEN = secrets.token_urlsafe(32)
    audit_event("web_token_rotated", source="web")
    return {"status": text.SESSION_TOKEN_ROTATED, "web_token": WEB_TOKEN}


@app.post(
    "/maintenance/reset_session",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def reset_session(request: Request):
    enforce_rate_limit(request)
    require_capability(Capability.SESSION_RESET)
    _require_restricted_when_field_mode(request)
    _rate_limit.clear()
    _restricted_sessions.pop(_restricted_session_token(request), None)
    return {"status": text.LOCAL_SESSION_COUNTERS_RESET}


@app.get(
    "/maintenance/diagnostics",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def diagnostics(request: Request):
    enforce_rate_limit(request)
    status_data = neutral_status()
    device_state = (
        "active"
        if status_data["device_state"] == "ready"
        else status_data["device_state"]
    )
    data = {
        "device_state": device_state,
        "camera_ready": status_data["camera_ready"],
        "object_state": status_data["object_state"],
        "local_mode": status_data["local_mode"],
        "restricted_confirmation_active": _restricted_session_valid(request),
    }
    restricted = _restricted_session_valid(request)
    if (not field_mode_enabled() or restricted) and capability_enabled(
        Capability.DIAGNOSTICS_DETAIL
    ):
        data.update(
            {
                "sensor_link": status_data["object_state"] != "none",
                "state_directory": state_dir(),
                "storage_node": _deceptive_path(state_dir()),
                "audit_enabled": os.environ.get("PHANTASM_AUDIT", "0").lower()
                not in {"0", "false", "off", "no"},
                "upload_limit_bytes": MAX_UPLOAD_BYTES,
            }
        )
    return data


@app.get(
    "/maintenance/logs",
    dependencies=[Depends(require_web_token), Depends(require_ui_unlock)],
)
async def export_logs(request: Request):
    enforce_rate_limit(request)
    require_capability(Capability.AUDIT_EXPORT)
    _require_restricted_when_field_mode(request)
    path = Path(state_dir()) / AUDIT_LOG_NAME
    if not path.exists():
        return JSONResponse(
            {"error": text.NO_LOCAL_EVENT_LOG}, status_code=404
        )
    data = path.read_bytes()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/jsonl",
        headers={"Content-Disposition": "attachment; filename=phantasm-events.jsonl"},
    )


def _maybe_auto_purge(accessed_mode, source):
    reason = None
    if duress_mode_enabled() and accessed_mode == gate.MODES[0]:
        reason = "duress_access"
    elif not purge_confirmation_required():
        reason = "confirmation_disabled"

    if reason is None:
        return False

    vault.purge_other_mode(accessed_mode)
    audit_event(
        "restricted_local_update",
        accessed_entry="local_entry",
        source=source,
        reason=reason,
    )
    return True


def _purge_for_password_role(accessed_mode, password_role, source):
    if password_role != GhostVault.PURGE_ROLE:
        return False
    vault.purge_other_mode(accessed_mode)
    audit_event(
        "restricted_local_update",
        accessed_entry="local_entry",
        source=source,
        reason="restricted_recovery",
    )
    return True


def create_file_response(content, filename, purge_applied=False):
    safe_filename = urllib.parse.quote("retrieved_payload.bin")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
            "X-Result-Filename": safe_filename,
        },
    )


if __name__ == "__main__":
    host = os.environ.get("PHANTASM_HOST", "127.0.0.1")
    port = int(os.environ.get("PHANTASM_PORT", "8000"))
    print(f"[WEB] Starting on http://{host}:{port}")
    print("[WEB] Mutating requests require X-Phantasm-Token from the served UI.")
    __import__("uvicorn").run(app, host=host, port=port)
