from errors import PatchError


def parse_pointer(pointer):
    """Return the list of reference tokens for a JSON pointer string."""
    if pointer == "":
        return []
    return pointer.split("/")[1:]
