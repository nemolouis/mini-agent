from errors import PatchError


def parse_pointer(pointer):
    """Return the list of reference tokens for a JSON pointer string."""
    if not isinstance(pointer, str):
        raise PatchError("pointer must be a string")
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise PatchError(f"invalid pointer: {pointer!r}")
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer[1:].split("/")]
