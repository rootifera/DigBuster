import re
from typing import Dict, Set

class DomainsError(Exception):
    pass

_LABEL_RE = re.compile(r"^[a-z0-9_-]{1,63}$", re.I)

def _valid_fqdn(name: str) -> bool:
    parts = name.split(".")
    if len(parts) < 2:
        return False
    return all(_LABEL_RE.match(p) for p in parts)

def load_domains(path: str) -> Dict[str, Set[str]]:
    contains: Set[str] = set()
    exact: Set[str] = set()
    wildcards: Set[str] = set()

    try:
        with open(path, "r", encoding="utf-8") as f:
            section = None
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1].strip().lower()
                    continue
                if section not in {"contains", "exact"}:
                    raise DomainsError(f"unknown or missing section before: {line}")

                entry = line.lower().strip().strip(".")
                if section == "contains":
                    contains.add(entry)
                    continue

                # [exact]
                if entry.startswith("*."):
                    base = entry[2:]
                    if not _valid_fqdn(base):
                        raise DomainsError(f"invalid wildcard base: {entry}")
                    wildcards.add(base)
                else:
                    if not _valid_fqdn(entry):
                        raise DomainsError(f"invalid fqdn: {entry}")
                    exact.add(entry)
    except FileNotFoundError:
        raise DomainsError(f"domains file not found: {path}")

    return {"contains": contains, "exact": exact, "wildcards": wildcards}


def classify_fqdn(fqdn: str, rules: dict) -> dict:
    """
    Return a structured match result for a fully-qualified domain name.

    rules: output of load_domains()
    -> {
         "hit": bool,
         "contains": set[str],   # which [contains] tokens matched (may be many)
         "exact": bool,          # True if exact FQDN matched in [exact]
         "wildcard": str | None  # base like "example.com" if matched a *.example.com rule
       }
    """
    name = fqdn.lower().strip().strip(".")
    contains_hits = {tok for tok in rules["contains"] if tok and tok in name}

    exact_hit = name in rules["exact"]

    wildcard_base = None
    if not exact_hit:
        for base in rules["wildcards"]:
            if name.endswith("." + base):
                wildcard_base = base
                break

    return {
        "hit": bool(contains_hits or exact_hit or wildcard_base),
        "contains": contains_hits,
        "exact": exact_hit,
        "wildcard": wildcard_base,
    }