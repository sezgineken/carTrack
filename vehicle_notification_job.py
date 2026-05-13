import smtplib
import sqlite3
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db.sqlite3"
ENV_PATH = BASE_DIR / ".env"


def load_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_receivers(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()] if raw else []


def parse_notification_days(raw: str) -> list[int]:
    if not raw:
        return [3]
    out = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            out.append(int(token))
        except ValueError:
            continue
    return sorted(set(out), reverse=True) if out else [3]


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cur.fetchall()}


def resolve_vehicle_history_date_columns(conn: sqlite3.Connection) -> dict[str, str]:
    cols = table_columns(conn, "vehicles_vehiclehistory")
    mapping = {
        "inspection": "inspection_date" if "inspection_date" in cols else "",
        "insurance": "insurance_date" if "insurance_date" in cols else "insurance_end_date" if "insurance_end_date" in cols else "",
        "casco": "casco_date" if "casco_date" in cols else "casco_end_date" if "casco_end_date" in cols else "",
    }
    missing = [key for key, col in mapping.items() if not col]
    if missing:
        raise RuntimeError(f"Date columns not found for: {', '.join(missing)}")
    return mapping


def date_from_db(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def fetch_vehicle_histories(conn: sqlite3.Connection, mapping: dict[str, str]) -> list[sqlite3.Row]:
    query = f"""
        SELECT
            v.id AS vehicle_id,
            v.plate AS plate,
            h.{mapping['inspection']} AS inspection_date,
            h.{mapping['insurance']} AS insurance_date,
            h.{mapping['casco']} AS casco_date
        FROM vehicles_vehicle v
        LEFT JOIN vehicles_vehiclehistory h ON h.vehicle_id = v.id
        WHERE v.is_active = 1
    """
    return conn.execute(query).fetchall()


def build_email_content(plate: str, notification_type: str, target_date: date, remaining_days: int) -> tuple[str, str]:
    type_label = {
        "inspection": "Muayene",
        "insurance": "Trafik Sigortasi",
        "casco": "Kasko",
    }.get(notification_type, notification_type)

    subject = f"[CarTrack] {plate} - {type_label} bitimine {remaining_days} gun"
    body = (
        "Arac son kullanma tarihi bildirimi\n\n"
        f"Plaka: {plate}\n"
        f"Tip: {type_label}\n"
        f"Bitis Tarihi: {target_date.isoformat()}\n"
        f"Kalan Gun: {remaining_days}\n\n"
        "Bu e-posta CarTrack bildirim gorevi tarafindan otomatik gonderilmistir."
    )
    return subject, body


def send_email(gmail_user: str, gmail_app_password: str, receivers: list[str], subject: str, body: str) -> None:
    if not gmail_user or not gmail_app_password:
        raise ValueError("Gmail credentials are missing.")
    if not receivers:
        raise ValueError("Mail receivers are missing.")

    message = MIMEMultipart()
    message["From"] = gmail_user
    message["To"] = ", ".join(receivers)
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_app_password.replace(" ", ""))
        server.sendmail(gmail_user, receivers, message.as_string())


def check_vehicle_dates() -> None:
    env = load_env(ENV_PATH)
    gmail_user = env.get("GMAIL_USER", "")
    gmail_app_password = env.get("GMAIL_APP_PASSWORD", "")
    receivers = parse_receivers(env.get("MAIL_RECEIVERS", ""))
    notification_days = parse_notification_days(env.get("NOTIFICATION_DAYS", "3"))

    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        mapping = resolve_vehicle_history_date_columns(conn)
        rows = fetch_vehicle_histories(conn, mapping)
        today = date.today()

        print(f"[INFO] Vehicles scanned: {len(rows)}")
        print(f"[INFO] Notification days: {notification_days}")

        sent_count = 0
        skipped_not_due = 0
        skipped_missing = 0

        for row in rows:
            plate = row["plate"]
            targets = {
                "inspection": date_from_db(row["inspection_date"]),
                "insurance": date_from_db(row["insurance_date"]),
                "casco": date_from_db(row["casco_date"]),
            }

            for ntype, target in targets.items():
                if target is None:
                    skipped_missing += 1
                    continue

                remaining_days = (target - today).days
                if remaining_days not in notification_days:
                    skipped_not_due += 1
                    continue

                subject, body = build_email_content(plate, ntype, target, remaining_days)
                try:
                    send_email(
                        gmail_user=gmail_user,
                        gmail_app_password=gmail_app_password,
                        receivers=receivers,
                        subject=subject,
                        body=body,
                    )
                except Exception as exc:
                    print(f"[ERROR] Mail send failed -> {plate} | {ntype} | {exc}")
                    continue

                sent_count += 1
                print(f"[SENT] {plate} | {ntype} | target={target.isoformat()} | remaining={remaining_days}")

        print(
            f"[DONE] sent={sent_count}, "
            f"skipped_not_due={skipped_not_due}, skipped_missing={skipped_missing}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    check_vehicle_dates()
