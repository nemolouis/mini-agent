"""Hard deny-list for bash commands. Anything not matched here still goes
through the normal confirmation prompt; this layer cannot be bypassed by --yes."""
import re

_DENY: list[tuple[str, str]] = [
    (r"\brm\s+(-\S+\s+)*-\S*[rR]\S*\s+(-\S+\s+)*(/|~|\$HOME|\*|\.\.?)(/?\s|/?$)", "recursive delete of /, ~, *, . or .."),
    (r"\bsudo\b", "sudo is not allowed"),
    (r"\bmkfs(\.\w+)?\b", "formatting filesystems"),
    (r"\bdd\b[^|;&]*\bof=/dev/", "writing to a block device"),
    (r">\s*/dev/(sd|nvme|disk)", "writing to a block device"),
    (r":\(\)\s*\{.*\};\s*:", "fork bomb"),
    (r"\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(ba|z)?sh\b", "piping a download into a shell"),
    (r"\bchmod\s+-R\s+0?777\s+/", "chmod -R 777 on /"),
    (r"\bgit\s+push\b[^;&|]*(--force\b|-f\b)", "force push"),
    (r"\bshutdown\b|\breboot\b|\bhalt\b", "power control"),
]
_COMPILED = [(re.compile(p), why) for p, why in _DENY]


def check_command(command: str) -> str | None:
    """Return a reason string if the command must be blocked, else None."""
    for pat, why in _COMPILED:
        if pat.search(command):
            return why
    return None
