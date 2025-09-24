"""
Notification helpers for DigBuster.

Supports:
- Pushover
- Gotify

Uses Python's standard library (urllib) to avoid extra dependencies.
"""

from typing import Tuple, Dict, Any
from urllib import request, parse, error
import json


class NotifyError(Exception):
    """Raised when a notification cannot be delivered."""


def _http_post_form(url: str, data: Dict[str, Any], headers: Dict[str, str] | None = None, timeout: int = 10) -> Tuple[int, str]:
    """
    POST application/x-www-form-urlencoded
    Returns (status_code, response_text[:500])
    """
    payload = parse.urlencode(data).encode("utf-8")
    req = request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.getcode(), body[:500]
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
        return e.code, body[:500]
    except Exception as e:
        raise NotifyError(str(e))


def _http_post_json(url: str, data: Dict[str, Any], headers: Dict[str, str] | None = None, timeout: int = 10) -> Tuple[int, str]:
    """
    POST application/json
    Returns (status_code, response_text[:500])
    """
    payload = json.dumps(data).encode("utf-8")
    req = request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.getcode(), body[:500]
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
        return e.code, body[:500]
    except Exception as e:
        raise NotifyError(str(e))


def send_pushover(ncfg: Dict[str, Any], title: str, message: str, priority: int = 0) -> Tuple[bool, str]:
    """
    Send a Pushover notification.
    ncfg must include:
      - pushover_user
      - pushover_token
    Returns (ok, status_text)
    """
    user = ncfg.get("pushover_user", "").strip()
    token = ncfg.get("pushover_token", "").strip()
    if not user or not token:
        return False, "pushover: missing user or token"

    url = "https://api.pushover.net/1/messages.json"
    form = {
        "token": token,
        "user": user,
        "title": title,
        "message": message,
        "priority": str(int(priority)),
    }
    code, body = _http_post_form(url, form)
    if code == 200:
        return True, "ok"
    return False, f"http-{code}:{body}"


def send_gotify(ncfg: Dict[str, Any], title: str, message: str, priority: int = 0) -> Tuple[bool, str]:
    """
    Send a Gotify notification.
    ncfg must include:
      - gotify_url (e.g., https://notify.example.com)
      - gotify_token
    Returns (ok, status_text)
    """
    base = ncfg.get("gotify_url", "").rstrip("/")
    token = ncfg.get("gotify_token", "").strip()
    if not base or not token:
        return False, "gotify: missing url or token"

    url = f"{base}/message"
    headers = {"X-Gotify-Key": token}
    payload = {
        "title": title,
        "message": message,
        "priority": int(priority),
    }
    code, body = _http_post_json(url, payload, headers=headers)
    if 200 <= code < 300:
        return True, "ok"
    return False, f"http-{code}:{body}"


def send_notification(cfg: Dict[str, Any], title: str, message: str, priority: int = 0) -> Tuple[bool, str]:
    """
    High-level entrypoint.

    cfg is the top-level config dict from load_config():
      cfg["notification"] = {
        "enabled": bool,
        "type": "pushover" | "gotify",
        ...provider keys...
      }

    Returns (ok, status_text)
    - If notifications are disabled, returns (False, "disabled") without raising.
    """
    ncfg = cfg.get("notification", {})
    if not ncfg.get("enabled", False):
        return False, "disabled"

    ntype = ncfg.get("type", "").lower()
    title = title or "DigBuster"
    message = message or ""

    if ntype == "pushover":
        return send_pushover(ncfg, title, message, priority=priority)
    if ntype == "gotify":
        return send_gotify(ncfg, title, message, priority=priority)

    return False, f"unknown-notifier:{ntype or 'unset'}"
