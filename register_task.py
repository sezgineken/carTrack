import csv
import subprocess
import sys
from pathlib import Path


TASK_NAME = "CarTrack Vehicle Notification Job"
START_TIME = "08:00"


def build_tr_command(python_exe: Path, job_script: Path) -> str:
    # Absolute paths are used, so working directory is not required.
    return f'"{python_exe}" "{job_script}"'


def register_task() -> None:
    project_dir = Path(__file__).resolve().parent
    job_script = project_dir / "vehicle_notification_job.py"
    python_exe = Path(sys.executable).resolve()

    if not job_script.exists():
        raise FileNotFoundError(f"Script not found: {job_script}")

    tr_command = build_tr_command(python_exe, job_script)
    cmd = [
        "schtasks",
        "/Create",
        "/TN",
        TASK_NAME,
        "/SC",
        "DAILY",
        "/ST",
        START_TIME,
        "/TR",
        tr_command,
        "/F",
    ]

    print("[INFO] Registering/updating task...")
    print(f"[INFO] Task name: {TASK_NAME}")
    print(f"[INFO] Python: {python_exe}")
    print(f"[INFO] Script: {job_script}")
    print(f"[INFO] Start time: {START_TIME}")
    result = subprocess.run(cmd, capture_output=True, text=True, shell=False)

    if result.returncode != 0:
        print("[ERROR] Failed to register task.")
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        raise SystemExit(result.returncode)

    print("[OK] Task registered successfully.")
    if result.stdout:
        print(result.stdout.strip())

    query_cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "CSV", "/NH"]
    query_result = subprocess.run(query_cmd, capture_output=True, text=True, shell=False)
    if query_result.returncode != 0:
        print("[WARN] Task status could not be read.")
        if query_result.stderr:
            print(query_result.stderr.strip())
        return

    status = "Unknown"
    line = (query_result.stdout or "").strip().splitlines()
    if line:
        try:
            row = next(csv.reader([line[0]]))
            if len(row) >= 3 and row[2].strip():
                status = row[2].strip()
        except Exception:
            status = "Unknown"

    print(f"[INFO] Task status: {status}")


if __name__ == "__main__":
    register_task()
