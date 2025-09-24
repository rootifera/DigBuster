from .config import load_config, ConfigError
from .domains import load_domains, DomainsError

DEFAULT_CONFIG = "config.cfg"
DEFAULT_DOMAINS = "domains.cfg"

def main():
    try:
        cfg = load_config(DEFAULT_CONFIG)
        dom = load_domains(DEFAULT_DOMAINS)
    except (ConfigError, DomainsError) as e:
        print(f"[digbuster] error: {e}")
        raise SystemExit(2)

    print("[digbuster] config OK")
    print(f"  log file  : {cfg['general']['dns_log_file']}")
    print(f"  notify    : {'enabled' if cfg['notification']['enabled'] else 'disabled'} ({cfg['notification']['type'] or 'n/a'})")
    if cfg['notification']['type'] == 'pushover':
        print(f"  pushover  : user={'set' if cfg['notification']['pushover_user'] else 'missing'}, token={'set' if cfg['notification']['pushover_token'] else 'missing'}")
    if cfg['notification']['type'] == 'gotify':
        print(f"  gotify    : url={'set' if cfg['notification']['gotify_url'] else 'missing'}, token={'set' if cfg['notification']['gotify_token'] else 'missing'}")

    print("[digbuster] domains OK")
    print(f"  contains  : {len(dom['contains'])}")
    print(f"  exact     : {len(dom['exact'])}")
    print(f"  wildcards : {len(dom['wildcards'])}")

if __name__ == "__main__":
    main()
