"""Trial-license enforcement for the TRIAL build.

Policy: the trial expires at whichever comes first —

* **7 days** after the very first launch, or
* **40 launches**.

State is kept in two places that are cross-checked so deleting one does not
reset the trial:

* a signed blob at ``%ProgramData%\\PHASEINV2\\.license.dat``
* a mirror under ``HKCU\\Software\\PHASEINV2`` (registry value ``s``)

Each field is reconciled to the *most conservative* value seen in either store
(earliest first-run, highest launch count, latest last-seen). The blob is signed
with an embedded HMAC key, so hand-editing it is detected and treated as an
expired/tampered trial. A backwards clock (now earlier than the last recorded
launch) is also treated as tampering.

This module is intentionally free of any Qt / UI dependency — the caller decides
how to present :class:`TrialStatus`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

TRIAL_DAYS = 7
TRIAL_MAX_LAUNCHES = 40

# Obfuscation/signing key baked into the build. Not a secret-grade protection
# (a determined user with the binary can bypass any client-side trial) — it just
# stops casual "edit the file / delete the file" resets.
_SIGNING_KEY = b"PHASEINV2-trial-2026-a7f3c1e9d84b25!keep-in-sync"
_REG_PATH = r"Software\PHASEINV2_Trial"
_REG_VALUE = "s"
_CLOCK_SKEW = timedelta(hours=6)  # tolerate small clock corrections/timezone drift


@dataclass
class TrialStatus:
    expired: bool
    reason: str            # "" while active; else a human (Arabic) reason
    days_left: int
    launches_left: int
    first_run: datetime
    launch_count: int

    @property
    def active(self) -> bool:
        return not self.expired


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_and_consume(now: datetime | None = None) -> TrialStatus:
    """Reconcile stored state, count this launch, persist, and return status.

    Call exactly once per application launch, before doing real work.
    """
    now = now or datetime.now()
    state = _reconcile(_load_file(), _load_registry())

    if state is None:
        # Brand-new trial starts now.
        state = {"first": _iso(now), "count": 0, "last": _iso(now)}

    first_run = _parse(state.get("first"), default=now)
    last_seen = _parse(state.get("last"), default=now)
    count = int(state.get("count", 0))

    # Tamper: clock moved backwards well beyond tolerated skew.
    clock_tampered = now + _CLOCK_SKEW < last_seen

    # This launch consumes one unit.
    count += 1
    state = {"first": _iso(first_run), "count": count, "last": _iso(now)}
    _save_file(state)
    _save_registry(state)

    days_used = (now - first_run).days
    days_left = max(0, TRIAL_DAYS - days_used)
    launches_left = max(0, TRIAL_MAX_LAUNCHES - count)

    reason = ""
    expired = False
    if clock_tampered:
        expired = True
        reason = "تم رصد تغيير في تاريخ/وقت النظام. برجاء ضبط التاريخ الصحيح."
    elif days_used >= TRIAL_DAYS:
        expired = True
        reason = f"انتهت الفترة التجريبية ({TRIAL_DAYS} أيام)."
    elif count > TRIAL_MAX_LAUNCHES:
        expired = True
        reason = f"انتهت الفترة التجريبية (تم استخدام {TRIAL_MAX_LAUNCHES} مرة تشغيل)."

    return TrialStatus(
        expired=expired,
        reason=reason,
        days_left=days_left,
        launches_left=launches_left,
        first_run=first_run,
        launch_count=count,
    )


def peek(now: datetime | None = None) -> TrialStatus | None:
    """Read current status WITHOUT consuming a launch (for display only)."""
    now = now or datetime.now()
    state = _reconcile(_load_file(), _load_registry())
    if state is None:
        return None
    first_run = _parse(state.get("first"), default=now)
    count = int(state.get("count", 0))
    days_used = (now - first_run).days
    expired = days_used >= TRIAL_DAYS or count >= TRIAL_MAX_LAUNCHES
    return TrialStatus(
        expired=expired,
        reason="",
        days_left=max(0, TRIAL_DAYS - days_used),
        launches_left=max(0, TRIAL_MAX_LAUNCHES - count),
        first_run=first_run,
        launch_count=count,
    )


# ---------------------------------------------------------------------------
# Signing / (de)serialisation
# ---------------------------------------------------------------------------


def _sign(payload: bytes) -> str:
    return hmac.new(_SIGNING_KEY, payload, hashlib.sha256).hexdigest()


def _encode(state: dict) -> str:
    payload = json.dumps(state, separators=(",", ":"), sort_keys=True).encode("utf-8")
    blob = {"d": base64.b64encode(payload).decode("ascii"), "m": _sign(payload)}
    return base64.b64encode(json.dumps(blob).encode("utf-8")).decode("ascii")


def _decode(text: str) -> dict | None:
    try:
        blob = json.loads(base64.b64decode(text.encode("ascii")))
        payload = base64.b64decode(blob["d"].encode("ascii"))
        if not hmac.compare_digest(_sign(payload), blob["m"]):
            return None  # tampered / wrong key
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


# ---------------------------------------------------------------------------
# File store
# ---------------------------------------------------------------------------


def _file_path() -> Path:
    program_data = os.environ.get("ProgramData") or os.path.expanduser("~")
    return Path(program_data) / "PHASEINV2_Trial" / ".license.dat"


def _load_file() -> dict | None:
    try:
        return _decode(_file_path().read_text(encoding="utf-8"))
    except OSError:
        return None


def _save_file(state: dict) -> None:
    path = _file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_encode(state), encoding="utf-8")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Registry mirror (HKCU — writable without admin)
# ---------------------------------------------------------------------------


def _load_registry() -> dict | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
            value, _ = winreg.QueryValueEx(key, _REG_VALUE)
        return _decode(str(value))
    except OSError:
        return None


def _save_registry(state: dict) -> None:
    if os.name != "nt":
        return
    try:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
            winreg.SetValueEx(key, _REG_VALUE, 0, winreg.REG_SZ, _encode(state))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Reconciliation helpers
# ---------------------------------------------------------------------------


def _reconcile(a: dict | None, b: dict | None) -> dict | None:
    """Merge two stores into the most conservative combined state."""
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    first_a = _parse(a.get("first"))
    first_b = _parse(b.get("first"))
    first = min(x for x in (first_a, first_b) if x is not None)
    last_a = _parse(a.get("last"))
    last_b = _parse(b.get("last"))
    lasts = [x for x in (last_a, last_b) if x is not None]
    last = max(lasts) if lasts else first
    count = max(int(a.get("count", 0)), int(b.get("count", 0)))
    return {"first": _iso(first), "count": count, "last": _iso(last)}


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _parse(value, default: datetime | None = None) -> datetime | None:
    if not value:
        return default
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return default
