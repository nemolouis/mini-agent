import re


def normalize_headers(headers):
    seen, out = {}, []
    for i, h in enumerate(headers, 1):
        name = re.sub(r"\s+", "_", h.strip().lower()) or f"column_{i}"
        seen[name] = seen.get(name, 0) + 1
        out.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    return out
