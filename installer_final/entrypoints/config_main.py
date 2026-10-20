"""Frozen entry point for the installer-only configuration helper (console).

Brand-new build (2026-08-22). Frozen to ``phaseinv2-config.exe`` and invoked by
the Inno Setup wizard to detect IPs, check ports, test the database, create it if
missing, provision the schema and write the encrypted connection profile. It runs
the exact same code path (:mod:`app.config.configure_cli`) the application uses,
so the installer and the running app never diverge.
"""

import os
import sys


def _add_project_root() -> None:
    if getattr(sys, "frozen", False):
        root = os.path.dirname(sys.executable)
    else:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


def main() -> int:
    _add_project_root()
    from app.config.configure_cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
