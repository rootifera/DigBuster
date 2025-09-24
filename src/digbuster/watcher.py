import os
import time
from pathlib import Path

from .config import load_config, ConfigError
from .domains import load_domains, DomainsError, classify_fqdn
from .extract import extract_fqdns
from .notify import send_notification

DEFAULT_CONFIG = "config.cfg"
DEFAULT_DOMAINS = "domains.cfg"


def _tail_f(path: str):
    """
    Tail a file forever (like `tail -F`), surviving log rotation.
    Yields new lines as they appear.
    """
    while True:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                current_inode = os.fstat(f.fileno()).st_ino

                while True:
                    line = f.readline()
                    if line:
                        yield line
                        continue

                    try:
                        st = os.stat(path)
                        if st.st_ino != current_inode:
                            break
                    except FileNotFoundError:
                        pass

                    time.sleep(0.2)

        except FileNotFoundError:
            time.sleep(0.5)


def _load_rules(domains_path: str):
    """Load domains rules, returning (rules_dict, mtime or 0)."""
    try:
        p = Path(domains_path)
        rules = load_domains(domains_path)
        mtime = p.stat().st_mtime if p.exists() else 0
        return rules, mtime
    except DomainsError as e:
        print(f"[digbuster] domains load error: {e}")
        return {"contains": set(), "exact": set(), "wildcards": set()}, 0


def watch():
    cfg = load_config(DEFAULT_CONFIG)

    logfile = cfg["general"]["dns_log_file"]
    cooldown = int(cfg["general"].get("cooldown_seconds", 60))

    domains_path = DEFAULT_DOMAINS
    rules, rules_mtime = _load_rules(domains_path)

    print(
        "[digbuster] watching "
        f"{logfile} (cooldown={cooldown}s, "
        f"contains={len(rules['contains'])}, exact={len(rules['exact'])}, wildcards={len(rules['wildcards'])})"
    )

    last_seen = {}
    last_rules_check = 0.0
    rules_check_interval = 1.0

    for raw in _tail_f(logfile):
        now_ts = time.time()
        if now_ts - last_rules_check >= rules_check_interval:
            last_rules_check = now_ts
            try:
                p = Path(domains_path)
                current_mtime = p.stat().st_mtime if p.exists() else 0
                if current_mtime and current_mtime != rules_mtime:
                    new_rules, new_mtime = _load_rules(domains_path)
                    rules = new_rules
                    rules_mtime = new_mtime
                    print(
                        f"[digbuster] domains reloaded "
                        f"(contains={len(rules['contains'])}, exact={len(rules['exact'])}, wildcards={len(rules['wildcards'])})"
                    )
            except Exception as e:
                print(f"[digbuster] domains reload warning: {e}")

        line = raw.rstrip("\n")
        if not line:
            continue

        fqdns = extract_fqdns(line)
        if not fqdns:
            continue

        now = time.time()
        for fq in fqdns:
            prev = last_seen.get(fq, 0.0)
            if now - prev < cooldown:
                continue

            res = classify_fqdn(fq, rules)
            if not res["hit"]:
                continue

            last_seen[fq] = now

            reasons = []
            if res["exact"]:
                reasons.append("exact")
            if res["wildcard"]:
                reasons.append(f"wildcard(*.{res['wildcard']})")
            if res["contains"]:
                reasons.append("contains:" + ",".join(sorted(res["contains"])))
            reason = "|".join(reasons) if reasons else "match"

            print(f"[MATCH] {fq} -> {reason}")
            print(f"        {line}")

            title = f"DigBuster: {fq}"
            msg = f"{reason}\n{line[:400]}"
            ok, status = send_notification(cfg, title, msg, priority=0)
            if not ok and status not in ("disabled",):
                print(f"[digbuster] notify error: {status}")

def main():
    try:
        watch()
    except (ConfigError, DomainsError) as e:
        print(f"[digbuster] error: {e}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
