# src/digbuster/config.py
from configparser import ConfigParser

class ConfigError(Exception):
    pass

def load_config(path: str) -> dict:
    """
    Load and validate DigBuster configuration from an INI-style file.
    """
    cp = ConfigParser()
    read = cp.read(path)
    if not read:
        raise ConfigError(f"config file not found or unreadable: {path}")

    if not cp.has_section("general"):
        raise ConfigError("missing [general] section")
    if not cp.has_section("notification"):
        raise ConfigError("missing [notification] section")

    dns_log_file = cp.get("general", "dns_log_file", fallback="").strip()
    if not dns_log_file:
        raise ConfigError("[general].dns_log_file must be set")

    cooldown = cp.getint("general", "cooldown_seconds", fallback=60)
    if cooldown < 0:
        raise ConfigError("[general].cooldown_seconds must be >= 0")

    enabled = cp.getboolean("notification", "enabled", fallback=False)
    ntype = cp.get("notification", "type", fallback="").strip().lower()
    if enabled and ntype not in {"pushover", "gotify"}:
        raise ConfigError('[notification].type must be "pushover" or "gotify" when enabled=true')

    cfg = {
        "general": {
            "dns_log_file": dns_log_file,
            "cooldown_seconds": cooldown,
        },
        "notification": {
            "enabled": enabled,
            "type": ntype,  # "" if disabled
            "pushover_user": cp.get("notification", "pushover_user", fallback="").strip(),
            "pushover_token": cp.get("notification", "pushover_token", fallback="").strip(),
            "gotify_url": cp.get("notification", "gotify_url", fallback="").strip(),
            "gotify_token": cp.get("notification", "gotify_token", fallback="").strip(),
        },
    }
    return cfg
