import re
from typing import Set

_DOMAIN_RE = re.compile(r'(?i)\b([a-z0-9_-]{1,63}(?:\.[a-z0-9_-]{1,63})+)\b')

def extract_fqdns(line: str) -> Set[str]:
    """
    Return a set of candidate FQDNs found in a log line.
    Trailing dots are stripped; output is lowercase.
    """
    if not line:
        return set()
    return {m.group(1).lower().strip(".") for m in _DOMAIN_RE.finditer(line)}
