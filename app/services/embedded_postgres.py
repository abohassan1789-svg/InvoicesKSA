"""Embedded / portable PostgreSQL server manager (trial build).

This lets the TRIAL edition run on a real PostgreSQL engine **without the
customer installing PostgreSQL**. The PostgreSQL binaries (``bin`` / ``lib`` /
``share``) are bundled inside the frozen application under ``pgsql\\`` and this
module drives their lifecycle:

* first launch  -> ``initdb`` creates a private data directory under
  ``%ProgramData%\\PHASEINV2\\pgdata`` (trust auth, listens on 127.0.0.1 only),
* every launch  -> ``pg_ctl start`` brings the server up on a private port
  (default 55432 so it never clashes with a "real" PostgreSQL on 5432),
* the application database is created if missing,
* the encrypted connection profile is (re)written to point the whole app at the
  embedded server, so ``app.config.settings`` / ``app.database`` need no changes,
* on process exit the server is stopped (``pg_ctl stop -m fast``).

Nothing here is specific to the trial *policy* — that lives in
``app.security.trial_guard``. This module only owns "make a local PostgreSQL
exist and be reachable".
"""

from __future__ import annotations

import atexit
import os
import subprocess
import sys
import time
from pathlib import Path

# Private port for the embedded server. Deliberately NOT 5432 so a machine that
# also has a normal PostgreSQL keeps working and the two never fight over a port.
EMBEDDED_PORT = 55432
EMBEDDED_HOST = "127.0.0.1"
SUPERUSER = "postgres"
APP_DB_NAME = "InvPhase2"

# Windows: keep every helper process windowless (the GUI app has no console).
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class EmbeddedPostgresError(RuntimeError):
    """Raised when the embedded server cannot be initialised or started."""


class EmbeddedPostgres:
    def __init__(
        self,
        pg_home: Path | None = None,
        data_dir: Path | None = None,
        port: int = EMBEDDED_PORT,
    ) -> None:
        self.pg_home = pg_home or _default_pg_home()
        self.data_dir = data_dir or _default_data_dir()
        self.port = port
        self._we_started_it = False

    # ---- binary paths ------------------------------------------------------

    @property
    def bin_dir(self) -> Path:
        return self.pg_home / "bin"

    def _exe(self, name: str) -> Path:
        exe = self.bin_dir / (name + (".exe" if os.name == "nt" else ""))
        if not exe.exists():
            raise EmbeddedPostgresError(
                f"مكوّن PostgreSQL المدمج غير موجود: {exe}. "
                "قد تكون نسخة التثبيت غير مكتملة."
            )
        return exe

    def _env(self) -> dict[str, str]:
        """Child-process environment with the bundled bin on PATH (for DLLs)."""
        env = dict(os.environ)
        env["PATH"] = str(self.bin_dir) + os.pathsep + env.get("PATH", "")
        # Never let a stray PGDATA/PGHOST from the host machine hijack us.
        for var in ("PGDATA", "PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGSERVICE"):
            env.pop(var, None)
        return env

    def _run(
        self, args: list[str], timeout: int = 120, capture: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a helper. ``capture=False`` is REQUIRED for ``pg_ctl start``.

        ``pg_ctl start`` launches a detached ``postgres`` that, on Windows,
        inherits any stdout/stderr *pipe* handles created by ``capture_output``.
        The pipe's read end then never reaches EOF and ``subprocess.run`` blocks
        for the entire lifetime of the server. Routing start's I/O to DEVNULL
        (no pipes) avoids that deadlock — the server log still goes to ``-l``.
        """
        if capture:
            return subprocess.run(
                args,
                cwd=str(self.bin_dir),
                env=self._env(),
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=_CREATE_NO_WINDOW,
            )
        return subprocess.run(
            args,
            cwd=str(self.bin_dir),
            env=self._env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )

    # ---- state -------------------------------------------------------------

    def is_initialized(self) -> bool:
        return (self.data_dir / "PG_VERSION").exists()

    def is_running(self) -> bool:
        """True if the server accepts connections on the private port."""
        try:
            result = self._run(
                [str(self._exe("pg_isready")), "-h", EMBEDDED_HOST,
                 "-p", str(self.port), "-t", "3"],
                timeout=15,
            )
        except Exception:
            return False
        return result.returncode == 0

    # ---- lifecycle ---------------------------------------------------------

    def initialize(self) -> None:
        """Create the data directory with ``initdb`` (idempotent-ish).

        Uses trust authentication (the server only ever listens on loopback) and
        a stable ``C`` / UTF-8 locale so ``initdb`` succeeds on any Windows
        regional setting.
        """
        if self.is_initialized():
            return
        # initdb requires the target directory to be empty (or absent). Only make
        # sure the PARENT exists — never drop a marker inside the data dir, or
        # initdb aborts with "directory exists but is not empty".
        self.data_dir.parent.mkdir(parents=True, exist_ok=True)

        result = self._run(
            [
                str(self._exe("initdb")),
                "-D", str(self.data_dir),
                "-U", SUPERUSER,
                "-A", "trust",
                "-E", "UTF8",
                "--locale-provider=libc",
                "--locale=C",
            ],
            timeout=300,
        )
        if result.returncode != 0:
            raise EmbeddedPostgresError(
                "فشل تهيئة قاعدة البيانات المحلية (initdb).\n"
                + (result.stderr or result.stdout or "")
            )
        self._write_server_config()

    def _write_server_config(self) -> None:
        """Pin the port, loopback-only listening and modest resource use."""
        conf = self.data_dir / "postgresql.conf"
        extra = (
            "\n# --- PHASEINV2 embedded (trial) overrides ---\n"
            f"port = {self.port}\n"
            "listen_addresses = '127.0.0.1'\n"
            "unix_socket_directories = ''\n"
            "max_connections = 50\n"
            "shared_buffers = 128MB\n"
            "fsync = on\n"
            "logging_collector = off\n"
        )
        try:
            with conf.open("a", encoding="utf-8") as fh:
                fh.write(extra)
        except OSError as exc:
            raise EmbeddedPostgresError(f"تعذّر كتابة إعدادات الخادم: {exc}") from exc

    def _clear_stale_pidfile(self) -> None:
        """A hard crash can leave postmaster.pid behind and block start."""
        pid = self.data_dir / "postmaster.pid"
        if pid.exists() and not self.is_running():
            try:
                pid.unlink()
            except OSError:
                pass

    def start(self, wait_seconds: int = 60) -> None:
        if self.is_running():
            return
        self._clear_stale_pidfile()
        log_file = self.data_dir / "server.log"
        result = self._run(
            [
                str(self._exe("pg_ctl")),
                "-D", str(self.data_dir),
                "-l", str(log_file),
                "-w", "-t", str(wait_seconds),
                "-o", f"-p {self.port}",
                "start",
            ],
            timeout=wait_seconds + 30,
            capture=False,   # MUST not capture: see _run() docstring (Windows deadlock).
        )
        # pg_ctl -w returns non-zero if it could not confirm startup; double-check
        # by polling pg_isready, because on a slow disk it sometimes times out the
        # wait yet the server comes up a second later.
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            if self.is_running():
                self._we_started_it = True
                atexit.register(self._atexit_stop)
                return
            time.sleep(1)
        raise EmbeddedPostgresError(
            "تعذّر تشغيل خادم قاعدة البيانات المحلي.\n"
            + (result.stderr or result.stdout or _tail(log_file))
        )

    def stop(self) -> None:
        if not self.is_initialized():
            return
        try:
            self._run(
                [str(self._exe("pg_ctl")), "-D", str(self.data_dir),
                 "-m", "fast", "-w", "-t", "30", "stop"],
                timeout=60,
            )
        except Exception:
            pass
        self._we_started_it = False

    def _atexit_stop(self) -> None:
        if self._we_started_it:
            self.stop()

    # ---- database ----------------------------------------------------------

    def ensure_database(self, name: str = APP_DB_NAME) -> None:
        """Create the application database if it does not already exist."""
        import psycopg
        from psycopg import sql

        dsn = f"host={EMBEDDED_HOST} port={self.port} dbname=postgres user={SUPERUSER}"
        with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", [name]
            ).fetchone()
            if not exists:
                conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))

    # ---- one-shot bootstrap ------------------------------------------------

    def bootstrap(self, db_name: str = APP_DB_NAME) -> None:
        """Init (if needed) -> start -> create DB -> write the connection profile.

        After this returns, the rest of the application (which reads the profile
        via ``app.config.settings``) is pointed at the embedded server and needs
        no knowledge that it is embedded.
        """
        self.initialize()
        self.start()
        self.ensure_database(db_name)
        _write_connection_profile(self.port, db_name)
        # Let the app's backup feature find the bundled pg_dump without PATH setup.
        os.environ.setdefault("PG_DUMP_PATH", str(self.bin_dir / "pg_dump.exe"))


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _default_pg_home() -> Path:
    """Where the bundled PostgreSQL binaries live.

    * Frozen (PyInstaller onedir): ``<_internal>/pgsql`` (added as data in the
      spec, so ``sys._MEIPASS`` points at ``_internal``).
    * Dev / source run: ``$PHASEINV2_PG_HOME`` if set, else the machine's own
      PostgreSQL install (so the trial code can be exercised before packaging).
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "pgsql"
    override = os.getenv("PHASEINV2_PG_HOME")
    if override:
        return Path(override)
    # Dev fallback: highest-versioned local install.
    for root in (r"C:\Program Files\PostgreSQL", r"C:\Program Files (x86)\PostgreSQL"):
        base = Path(root)
        if base.is_dir():
            versions = sorted(
                (p for p in base.iterdir() if (p / "bin").is_dir()),
                key=lambda p: p.name, reverse=True,
            )
            if versions:
                return versions[0]
    return Path("pgsql")


def _default_data_dir() -> Path:
    # Isolated from a production PHASEINV2 install: the trial keeps its own data
    # tree so installing it next to the full version never touches the real
    # cluster or connection profile.
    program_data = os.environ.get("ProgramData") or os.path.expanduser("~")
    return Path(program_data) / "PHASEINV2_Trial" / "pgdata"


def _tail(path: Path, lines: int = 20) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(content[-lines:])
    except OSError:
        return ""


def _write_connection_profile(port: int, db_name: str) -> None:
    """Point the app's connection profile at the embedded local server.

    Reuses the existing encrypted-profile machinery so nothing else in the app
    needs to know the database is embedded.
    """
    try:
        from app.config import connection_config as cc

        profile = cc.ConnectionProfile(
            connection_mode=cc.MODE_LAN,
            server_address=EMBEDDED_HOST,
            server_port=port,
            db_name=db_name,
            db_user=SUPERUSER,
            db_password="",          # trust auth on loopback
            sslmode="disable",
        )
        cc.save(profile)
    except Exception:
        # A profile-write failure is not fatal: the server is up and the app's
        # first-run screen can still recover. Do not crash the launch over it.
        pass
