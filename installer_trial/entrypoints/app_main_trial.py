"""Frozen entry point for the PHASEINV2 **TRIAL** desktop application.

Startup order (all before the normal app runs):

  1. Make the bundled ``app`` package importable and redirect writable data to
     ``%ProgramData%\\PHASEINV2`` (same as the production entry point).
  2. Enforce the trial policy (7 days OR 40 launches — see ``trial_guard``).
     If it is over, show a message and quit.
  3. Bring up the **embedded** PostgreSQL server (no PostgreSQL install on the
     customer's machine) and point the connection profile at it.
  4. Hand off to the normal application (``app.main.main``), which now finds a
     reachable database and provisions its schema automatically.

Any unhandled startup error is written to
``%ProgramData%\\PHASEINV2\\logs\\app-startup-error.log`` because a windowed
build has no console.
"""

import os
import sys


def _data_dir() -> str:
    # Trial keeps ALL its writable data (embedded cluster, license, logs,
    # backups, connection profile) in its own folder, fully isolated from a
    # production PHASEINV2 install on the same machine.
    program_data = os.environ.get("ProgramData") or os.path.expanduser("~")
    return os.path.join(program_data, "PHASEINV2_Trial")


def _add_project_root() -> None:
    if getattr(sys, "frozen", False):
        return
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


def _chosen_backup_dir(settings_path: str) -> str:
    try:
        import json

        with open(settings_path, encoding="utf-8") as fh:
            data = json.load(fh)
        chosen = data.get("backup_dir") if isinstance(data, dict) else None
        return str(chosen).strip() if chosen else ""
    except (OSError, ValueError):
        return ""


def _configure_frozen_runtime() -> None:
    if not getattr(sys, "frozen", False):
        return
    data_dir = _data_dir()
    settings_path = os.path.join(data_dir, "backup_settings.json")
    backups_dir = _chosen_backup_dir(settings_path) or os.path.join(data_dir, "Backups")
    try:
        os.makedirs(backups_dir, exist_ok=True)
    except OSError:
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


def _pin_connection_profile() -> None:
    """Force the app to use the embedded server's own connection profile.

    ``config_path()`` honours ``PHASEINV2_CONFIG_PATH`` above everything else, so
    pinning it here makes the trial deterministic no matter what a stray ``.env``
    or a machine-wide ``CRM_CONFIG_PATH`` might otherwise point at. The embedded
    PostgreSQL bootstrap writes the profile to this exact path.
    """
    profile_path = os.path.join(_data_dir(), "connection.json")
    os.environ["PHASEINV2_CONFIG_PATH"] = profile_path
    # Neutralise any inherited overrides that would send the app to a different
    # (non-embedded) database.
    for stray in ("CRM_CONFIG_PATH", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        os.environ.pop(stray, None)


def _log_startup_error(exc: BaseException) -> None:
    import traceback

    try:
        logs_dir = os.path.join(_data_dir(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        path = os.path.join(logs_dir, "app-startup-error.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("=== trial startup error ===\n")
            fh.write("frozen=%s executable=%s\n" % (getattr(sys, "frozen", False), sys.executable))
            traceback.print_exc(file=fh)
            fh.write("\n")
    except Exception:
        pass


def _make_app():
    """Create (or reuse) the QApplication with the app's RTL defaults."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    return app


def _enforce_trial(app) -> bool:
    """Return True to continue, False if the trial is over (message shown)."""
    from PySide6.QtWidgets import QMessageBox

    from app.security import trial_guard

    status = trial_guard.check_and_consume()
    if status.expired:
        box = QMessageBox()
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("النسخة التجريبية")
        box.setText(status.reason + "\n\nبرجاء التواصل مع المورّد لتفعيل النسخة الكاملة.")
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()
        return False

    # A gentle heads-up as the trial nears its end (non-blocking-ish).
    if status.days_left <= 2 or status.launches_left <= 5:
        QMessageBox.information(
            None,
            "النسخة التجريبية",
            f"نسخة تجريبية — المتبقّي: {status.days_left} يوم "
            f"أو {status.launches_left} مرة تشغيل.",
        )
    return True


def _start_embedded_db(app) -> bool:
    """Bring up the bundled PostgreSQL. Return True on success."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox, QSplashScreen
    from PySide6.QtGui import QPixmap

    splash = QSplashScreen(QPixmap(1, 1))
    splash.showMessage(
        "جارٍ تجهيز قاعدة البيانات المحلية لأول مرة، برجاء الانتظار...",
        Qt.AlignCenter, Qt.black,
    )
    splash.show()
    app.processEvents()
    try:
        from app.services.embedded_postgres import EmbeddedPostgres

        EmbeddedPostgres().bootstrap()
        splash.close()
        return True
    except Exception as exc:  # noqa: BLE001
        splash.close()
        _log_startup_error(exc)
        QMessageBox.critical(
            None,
            "قاعدة البيانات المحلية",
            "تعذّر تشغيل قاعدة البيانات المحلية المدمجة.\n\n"
            + str(exc)
            + "\n\nبرجاء إعادة تشغيل البرنامج، وإن استمرت المشكلة تواصل مع المورّد.",
        )
        return False


def main() -> int:
    try:
        _add_project_root()
        _configure_frozen_runtime()
        _pin_connection_profile()

        app = _make_app()

        if not _enforce_trial(app):
            return 2
        if not _start_embedded_db(app):
            return 3

        from app.main import main as app_main

        app_main()
        return 0
    except BaseException as exc:  # noqa: BLE001
        _log_startup_error(exc)
        raise


if __name__ == "__main__":
    sys.exit(main())
