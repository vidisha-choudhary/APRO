"""Helper script to set up PostgreSQL for acceptance testing."""

import os
import subprocess
import sys
from pathlib import Path

DEFAULT_PG_URL = "postgresql+asyncpg://postgres@127.0.0.1:5432/apro_test_db"


def setup_local_postgres() -> str:
    """Ensure PostgreSQL is running locally and return connection string."""
    base_dir = Path("C:/Users/ASUS/pg16_portable")
    bin_dir = base_dir / "pgsql" / "bin"
    data_dir = base_dir / "pgsql" / "data"
    log_file = base_dir / "pgsql" / "logfile.log"

    if not bin_dir.exists():
        print(f"PostgreSQL binary directory not found at {bin_dir}")
        sys.exit(1)

    initdb = bin_dir / "initdb.exe"
    pg_ctl = bin_dir / "pg_ctl.exe"
    createdb = bin_dir / "createdb.exe"

    if not data_dir.exists():
        print("Initializing PostgreSQL data directory...")
        subprocess.run(
            [str(initdb), "-D", str(data_dir), "-U", "postgres", "--auth=trust"],
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

    # Create apro_test_db if it doesn't exist
    print("Ensuring apro_test_db exists...")
    subprocess.run(
        [
            str(createdb),
            "-U",
            "postgres",
            "-h",
            "127.0.0.1",
            "-p",
            "5432",
            "apro_test_db",
        ],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    db_url = os.getenv("POSTGRES_TEST_URL", DEFAULT_PG_URL)
    print("PostgreSQL setup complete. Server is active and accepting connections.")
    return db_url


if __name__ == "__main__":
    setup_local_postgres()
