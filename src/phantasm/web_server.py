from fastapi import FastAPI, UploadFile, File, Form, Request, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from .ai_gate import gate, get_gesture_sequence
from .audit import audit_event
from .config import duress_mode_enabled, purge_confirmation_required
from .gv_core import GhostVault
import uvicorn
import io
import os
import secrets
import time
import urllib.parse
from pathlib import Path

app = FastAPI(title="Phantasm - Tactical Secure Interface")
templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
vault = GhostVault("vault.bin")
WEB_TOKEN = os.environ.get("PHANTASM_WEB_TOKEN") or secrets.token_urlsafe(32)
MAX_UPLOAD_BYTES = int(os.environ.get("PHANTASM_MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 20
_rate_limit = {}
MODE_LABELS = {
    "dummy": "Profile A",
    "secret": "Profile B",
}
PROFILE_TO_MODE = {
    "profile_a": "dummy",
    "profile_b": "secret",
}


def display_mode_label(mode):
    return MODE_LABELS.get(mode, "Profile")


def resolve_mode(profile_value):
    if profile_value not in PROFILE_TO_MODE:
        raise ValueError(f"unsupported profile: {profile_value}")
    return PROFILE_TO_MODE[profile_value]


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

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "web_token": WEB_TOKEN,
            "max_upload_bytes": MAX_UPLOAD_BYTES,
            "purge_confirmation_required": str(purge_confirmation_required()).lower(),
            "duress_mode_enabled": str(duress_mode_enabled()).lower(),
        },
    )

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(gate.generate_frames(), 
                             media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/status")
async def status():
    status = gate.get_status()
    matched_mode = status.get("matched_mode")
    if matched_mode in MODE_LABELS:
        status["matched_profile"] = display_mode_label(matched_mode)
    else:
        status["matched_profile"] = None
    return status

@app.post("/register_key", dependencies=[Depends(require_web_token)])
async def register_key(request: Request, profile: str = Form(...), replace: bool = Form(False)):
    enforce_rate_limit(request)
    mode = resolve_mode(profile)
    if gate.get_status()["registered_modes"].get(mode) and not replace:
        return {"error": f"{display_mode_label(mode)} already has an image key. Confirm replacement first."}
    success, message = gate.capture_reference(mode)
    if success:
        audit_event("image_key_registered", profile=display_mode_label(mode), source="web")
        return {"status": f"{display_mode_label(mode)} image key registered."}
    return {"error": message}

@app.post("/store", dependencies=[Depends(require_web_token)])
async def store(request: Request,
                file: UploadFile = File(...),
                password: str = Form(...), 
                profile: str = Form("profile_a")):
    enforce_rate_limit(request)
    
    data = await read_limited_upload(file)
    orig_filename = file.filename
    
    try:
        mode = resolve_mode(profile)
        if not gate.get_status()["registered_modes"].get(mode):
            return {"error": f"No image key is registered for {display_mode_label(mode)}."}

        vault.store(
            password,
            data,
            gate.sequence_for_mode(mode),
            filename=orig_filename,
            mode=mode,
        )
        audit_event("payload_stored", profile=display_mode_label(mode), filename=orig_filename, bytes=len(data), source="web")
        return {"status": f"Payload '{orig_filename}' committed to {display_mode_label(mode)}."}
    except Exception as e:
        return {"error": str(e)}

@app.post("/retrieve", dependencies=[Depends(require_web_token)])
async def retrieve(request: Request, password: str = Form(...)):
    enforce_rate_limit(request)
    auth_sequence = get_gesture_sequence(length=1)
    if gate.last_match_mode == gate.MATCH_AMBIGUOUS:
        return {"error": "Authentication failed: both registered keys match the presented object."}
    if auth_sequence[0] == gate.MATCH_NONE:
        return {"error": "Authentication failed: no registered image key matched."}

    result, filename = vault.retrieve(password, auth_sequence, mode="dummy")
    if result is not None:
        audit_event("payload_retrieved", profile=display_mode_label("dummy"), filename=filename, bytes=len(result), source="web")
        _maybe_auto_purge("dummy", source="web")
        return create_file_response(result, filename or "profile-a.bin", accessed_profile="profile_a")

    result, filename = vault.retrieve(password, auth_sequence, mode="secret")
    if result is not None:
        audit_event("payload_retrieved", profile=display_mode_label("secret"), filename=filename, bytes=len(result), source="web")
        _maybe_auto_purge("secret", source="web")
        return create_file_response(result, filename or "profile-b.bin", accessed_profile="profile_b")
    
    audit_event("retrieve_failed", source="web")
    return {"error": "Authentication failed."}


@app.post("/purge_other", dependencies=[Depends(require_web_token)])
async def purge_other(request: Request, accessed_profile: str = Form(...), confirmation: str = Form(...)):
    enforce_rate_limit(request)
    mode = resolve_mode(accessed_profile)
    other_mode = "secret" if mode == "dummy" else "dummy"
    expected = f"DELETE {display_mode_label(other_mode).upper()}"
    if purge_confirmation_required() and confirmation != expected:
        return {"error": f"Confirmation required: {expected}"}

    vault.purge_other_mode(mode)
    audit_event("alternate_profile_purged", accessed_profile=display_mode_label(mode), source="web")
    return {"status": f"Alternate profile ({display_mode_label(other_mode)}) purged."}


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
        "alternate_profile_purged",
        accessed_profile=display_mode_label(accessed_mode),
        source=source,
        reason=reason,
    )
    return True

def create_file_response(content, filename, accessed_profile=None):
    # Support UTF-8 filenames in downloads.
    safe_filename = urllib.parse.quote(filename)
    return StreamingResponse(
        io.BytesIO(content), 
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
            "X-Filename": safe_filename,
            "X-Accessed-Profile": accessed_profile or "",
        }
    )

if __name__ == "__main__":
    host = os.environ.get("PHANTASM_HOST", "127.0.0.1")
    port = int(os.environ.get("PHANTASM_PORT", "8000"))
    print(f"[WEB] Starting on http://{host}:{port}")
    print("[WEB] Mutating requests require X-Phantasm-Token from the served UI.")
    uvicorn.run(app, host=host, port=port)
