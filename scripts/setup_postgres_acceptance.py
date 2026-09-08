"""Helper script to set up PostgreSQL for acceptance testing."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def setup_local_postgres() -> str:
    """Ensure PostgreSQL is running locally and return the explicit test connection string."""
    # 1. Require explicit target database URL via POSTGRES_TEST_URL
    db_url = os.getenv("POSTGRES_TEST_URL")
    if not db_url or not db_url.strip():
        print(
            "ERROR: POSTGRES_TEST_URL environment variable is missing or empty.\n\n"
            "The caller must explicitly provide the intended acceptance database URL.\n"
            "The setup helper does not silently choose or default to any database.\n\n"
            "Examples:\n"
            "  PowerShell: $env:POSTGRES_TEST_URL='postgresql+asyncpg://<user>:<password>@127.0.0.1:5432/<target_acceptance_db>'\n"
            "  Bash:       export POSTGRES_TEST_URL='postgresql+asyncpg://<user>:<password>@127.0.0.1:5432/<target_acceptance_db>'\n"
        )
        sys.exit(1)

    # Resolve target database parameters from POSTGRES_TEST_URL
    parsed = urlparse(db_url)
    target_db = parsed.path.lstrip("/")
    if not target_db:
        print(
            "ERROR: POSTGRES_TEST_URL is invalid or does not contain a database name.\n"
            "The URL must include a database name path, e.g. .../apro_attack_db."
        )
        sys.exit(1)

    # Fail-closed protection: never allow acceptance setup helper to target apro_test_db
    if target_db == "apro_test_db":
        print(
            "CRITICAL TOPOLOGY ERROR: Target database cannot be 'apro_test_db'.\n"
            "The acceptance setup helper must NEVER operate on or mutate the canonical\n"
            "judge/demo database ('apro_test_db'). Please configure a dedicated test\n"
            "or acceptance database (e.g. 'apro_attack_db' or 'apro_phase18_acceptance_db')."
        )
        sys.exit(1)

    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 5432)
    user = parsed.username or "postgres"

    # 2. Search for PostgreSQL binaries in system PATH
    system_createdb = shutil.which("createdb") or shutil.which("createdb.exe")
    if system_createdb:
        print(
            f"Found PostgreSQL tools in system PATH. Ensuring target database '{target_db}' exists..."
        )
        subprocess.run(
            [
                system_createdb,
                "-U",
                user,
                "-h",
                host,
                "-p",
                port,
                target_db,
            ],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
        print(
            f"PostgreSQL setup complete. Database '{target_db}' is ready and server is active."
        )
        return db_url

    # 3. If not found in PATH, check for explicit PG_PORTABLE_PATH environment variable
    portable_env = os.getenv("PG_PORTABLE_PATH")
    if not portable_env:
        print(
            "ERROR: PostgreSQL binaries ('createdb') not found in system PATH, "
            "and PG_PORTABLE_PATH environment variable is unset.\n\n"
            "Please either:\n"
            "  1. Ensure standard PostgreSQL is installed and its bin directory is on system PATH, OR\n"
            "  2. Set PG_PORTABLE_PATH to your portable PostgreSQL root directory before running this script:\n"
            "     PowerShell: $env:PG_PORTABLE_PATH='<path_to_portable_postgres_root>'\n"
            "     Bash:       export PG_PORTABLE_PATH='<path_to_portable_postgres_root>'\n"
        )
        sys.exit(1)

    # 4. If PG_PORTABLE_PATH is provided, resolve and verify binary directories
    base_dir = Path(portable_env)
    bin_dir = base_dir / "pgsql" / "bin"
    data_dir = base_dir / "pgsql" / "data"
    log_file = base_dir / "pgsql" / "logfile.log"

    if not bin_dir.exists():
        if (base_dir / "bin").exists():
            bin_dir = base_dir / "bin"
            data_dir = base_dir / "data"
            log_file = base_dir / "logfile.log"
        else:
            print(
                f"ERROR: PostgreSQL binary directory not found at {bin_dir}.\n"
                f"Please verify the directory structure in PG_PORTABLE_PATH ('{portable_env}')."
            )
            sys.exit(1)

    initdb = bin_dir / ("initdb.exe" if sys.platform == "win32" else "initdb")
    pg_ctl = bin_dir / ("pg_ctl.exe" if sys.platform == "win32" else "pg_ctl")
    createdb = bin_dir / ("createdb.exe" if sys.platform == "win32" else "createdb")

    if not data_dir.exists():
        print("Initializing PostgreSQL data directory...")
        subprocess.run(
            [str(initdb), "-D", str(data_dir), "-U", user, "--auth=trust"],
            check=True,
        )

    # Check if server is running
    status_res = subprocess.run(
        [str(pg_ctl), "-D", str(data_dir), "status"],
        capture_output=True,
    )
    if status_res.returncode != 0:
        print("Starting PostgreSQL server...")
        subprocess.run(
            [str(pg_ctl), "-D", str(data_dir), "-l", str(log_file), "start"],
            check=True,
        )

    # Create target database if it doesn't exist
    print(f"Ensuring target database '{target_db}' exists...")
    subprocess.run(
        [
            str(createdb),
            "-U",
            user,
            "-h",
            host,
            "-p",
            port,
            target_db,
        ],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    print(
        f"PostgreSQL setup complete. Database '{target_db}' is ready and server is active."
    )
    return db_url


if __name__ == "__main__":
    setup_local_postgres()
