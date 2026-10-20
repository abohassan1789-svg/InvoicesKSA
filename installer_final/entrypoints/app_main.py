"""Frozen entry point for the PHASEINV2 desktop application (GUI, windowed).

Brand-new build (2026-08-22). This shim does three things:

  * Makes the bundled ``app`` package importable both from source and when frozen.
  * Only when frozen, redirects the app's *writable* data (backups, settings and
    any relative-path writes) to ``%ProgramData%\\PHASEINV2`` so the app never
    writes inside a read-only ``Program Files`` install and runs without admin.
  * Captures any unhandled startup exception to
    ``%ProgramData%\\PHASEINV2\\logs\\app-startup-error.log`` — a ``--windowed``
    build has no console, so this is the only way such a failure is diagnosable.
"""

import os
import sys


def _data_dir() -> str:
    program_data = os.environ.get("ProgramData") or os.path.expanduser("~")
    return os.path.join(program_data, "PHASEINV2")


def _add_project_root() -> None:
    if getattr(sys, "frozen", False):
        # Frozen: the bundled ``app`` package is importable from the bundle's
        # ``_internal`` directory. Prepending the exe dir would shadow it.
        return
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


def _chosen_backup_dir(settings_path: str) -> str:
    """The backup folder the administrator picked at install time, if any.

    The installer records it under ``backup_dir`` in ``backup_settings.json``.
    Best-effort: a missing/unreadable file means "use the default", not an error.
    """
    try:
        import json

        with open(settings_path, encoding="utf-8") as fh:
            data = json.load(fh)
        chosen = data.get("backup_dir") if isinstance(data, dict) else None
        return str(chosen).strip() if chosen else ""
    except (OSError, ValueError):
        return ""


def _configure_frozen_runtime() -> None:
    """Point writable data at a per-machine, user-writable directory (frozen only)."""
    if not getattr(sys, "frozen", False):
        return

    data_dir = _data_dir()
    settings_path = os.path.join(data_dir, "backup_settings.json")
    # The installer's chosen folder wins over the ProgramData default, otherwise
    # the wizard's "Backup folder" page would be decorative.
    backups_dir = _chosen_backup_dir(settings_path) or os.path.join(data_dir, "Backups")
    try:
        os.makedirs(backups_dir, exist_ok=True)
    except OSError:
        # A chosen folder on an unplugged external/network drive must not stop
        # the app from opening: fall back to the always-present local default.
        backups_dir = os.path.join(data_dir, "Backups")
        try:
            os.makedirs(backups_dir, exist_ok=True)
        except OSError:
            return

    os.environ.setdefault("BACKUP_DIR", backups_dir)
    os.environ.setdefault("BACKUP_SETTINGS_PATH", settings_path)
    try:
        os.chdir(data_dir)
    except OSError:
        pass


def _log_startup_error(exc: BaseException) -> None:
    """Best-effort: write a startup traceback so windowed builds are diagnosable."""
    import traceback

    try:
        logs_dir = os.path.join(_data_dir(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        path = os.path.join(logs_dir, "app-startup-error.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("=== startup error ===\n")
            fh.write("frozen=%s executable=%s\n" % (getattr(sys, "frozen", False), sys.executable))
            fh.write("sys.path=%r\n" % (sys.path,))
            traceback.print_exc(file=fh)
            fh.write("\n")
    except Exception:
        pass


def main() -> int:
    try:
        _add_project_root()
        _configure_frozen_runtime()
        from app.main import main as app_main

        app_main()
        return 0
    except BaseException as exc:  # noqa: BLE001 - capture, log, then re-raise
        _log_startup_error(exc)
        raise


if __name__ == "__main__":
    sys.exit(main())
