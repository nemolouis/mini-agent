from errors import CycleError  # noqa: F401


def build_order(deps):
    """deps: {package: [dependencies]} -> packages, dependencies first."""
    order, seen = [], set()

    def visit(n):
        if n in seen:
            return
        seen.add(n)
        for d in deps.get(n, []):
            visit(d)
        order.append(n)

    for n in deps:
        visit(n)
    return order
