from constraints import satisfies, vtuple


class ResolutionError(Exception):
    pass


def resolve(index, requirements):
    """Return {package: version} satisfying `requirements` ({name: constraint}) and all
    transitive dependencies, or raise ResolutionError if no assignment exists.

    Among valid assignments prefer newer versions: packages are decided in the order they
    are first required, trying each package's newest version first. If a choice leads to a
    dead end, other versions (and earlier choices) must be tried before giving up.
    Versions compare numerically ('1.10.0' is newer than '1.9.0')."""

    def search(chosen, cons, todo):
        if not todo:
            return chosen
        name, rest = todo[0], todo[1:]
        for v in sorted(index.versions(name), key=vtuple, reverse=True):
            if not all(satisfies(v, s) for s in cons.get(name, [])):
                continue
            deps = index.deps(name, v)
            cons2 = {k: list(vs) for k, vs in cons.items()}
            ok = True
            for dn, spec in deps.items():
                cons2.setdefault(dn, []).append(spec)
                if dn in chosen and not satisfies(chosen[dn], spec):
                    ok = False
                    break
            if not ok:
                continue
            todo2 = rest + [d for d in deps if d not in chosen and d not in rest and d != name]
            result = search({**chosen, name: v}, cons2, todo2)
            if result is not None:
                return result
        return None

    result = search({}, {n: [s] for n, s in requirements.items()}, list(requirements))
    if result is None:
        raise ResolutionError("no consistent set of versions satisfies the requirements")
    return result
