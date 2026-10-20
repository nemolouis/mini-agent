from errors import CycleError


def build_order(deps):
    """deps: {package: [dependencies]} -> packages, dependencies first."""
    order, state = [], {}

    def visit(n):
        s = state.get(n)
        if s == "done":
            return
        if s == "active":
            raise CycleError(n)
        state[n] = "active"
        for d in sorted(deps.get(n, [])):
            visit(d)
        state[n] = "done"
        order.append(n)

    nodes = set(deps) | {d for ds in deps.values() for d in ds}
    for n in sorted(nodes):
        visit(n)
    return order
