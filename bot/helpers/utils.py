import re
from datetime import datetime, timezone


def format_time(seconds):
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m = seconds // 60
        s = seconds % 60
        return f"{m}m {s}s" if s else f"{m}m"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m" if m else f"{h}h"


def parse_interval(text):
    text = text.strip().lower()
    match = re.match(r"^(\d+)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hour|hours)?$", text)
    if not match:
        try:
            return int(text)
        except ValueError:
            return None
    value = int(match.group(1))
    unit = match.group(2) or "s"
    if unit.startswith("m"):
        return value * 60
    elif unit.startswith("h"):
        return value * 3600
    return value


def is_valid_link(link):
    patterns = [
        r"https?://t\.me/\+[\w-]+",
        r"https?://t\.me/joinchat/[\w-]+",
        r"https?://t\.me/[\w]+",
        r"@[\w]+",
    ]
    for pattern in patterns:
        if re.match(pattern, link.strip()):
            return True
    return False


def extract_links(text):
    links = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line and is_valid_link(line):
            links.append(line)
    return links


async def send_log_message(text):
    """Bypasses Pyrogram's cache completely and sends log directly via HTTP."""
    from bot import config
    import requests
    
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.LOG_GROUP,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass


async def send_error_log(app, error, user_id, context="Unknown"):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    text = (
        f"<b>Error Report</b>\n\n"
        f"<b>User:</b> <code>{user_id}</code>\n"
        f"<b>Context:</b> <code>{context}</code>\n"
        f"<b>Time:</b> <code>{now}</code>\n"
        f"<b>Error:</b> <code>{str(error)[:500]}</code>"
    )
    await send_log_message(text)


def format_phone(phone):
    if not phone:
        return "Unknown"
    if phone.startswith("+"):
        return phone[:4] + "****" + phone[-3:]
    return phone[:3] + "****" + phone[-3:]
