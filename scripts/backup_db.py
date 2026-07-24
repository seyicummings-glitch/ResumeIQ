import os
import subprocess
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")


def run_backup():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set.")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = os.path.join(BACKUP_DIR, f"resumeiq_backup_{timestamp}.dump")

    subprocess.run(
        ["pg_dump", database_url, "-Fc", "-f", output_path],
        check=True
    )
    print(f"Backup written to {output_path}")


if __name__ == "__main__":
    run_backup()
