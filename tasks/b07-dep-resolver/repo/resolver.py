from constraints import satisfies


class ResolutionError(Exception):
    pass


def resolve(index, requirements):
    """Return {package: version} satisfying `requirements` ({name: constraint}) and all
    transitive dependencies, or raise ResolutionError if no assignment exists.

    Among valid assignments prefer newer versions: packages are decided in the order they
    are first required, trying each package's newest version first. If a choice leads to a
    dead end, other versions (and earlier choices) must be tried before giving up.
    Versions compare numerically ('1.10.0' is newer than '1.9.0')."""
    chosen = {}
    cons = {n: [s] for n, s in requirements.items()}
    todo = list(requirements)
    while todo:
        name = todo.pop(0)
        if name in chosen:
            continue
        cands = [v for v in sorted(index.versions(name), reverse=True)
                 if all(satisfies(v, s) for s in cons.get(name, []))]
        if not cands:
            raise ResolutionError(f"no version of {name} satisfies {cons.get(name)}")
        v = cands[0]
        chosen[name] = v
        for dn, spec in index.deps(name, v).items():
            cons.setdefault(dn, []).append(spec)
            if dn in chosen and not satisfies(chosen[dn], spec):
                raise ResolutionError(f"{dn} {chosen[dn]} conflicts with {spec}")
            if dn not in chosen and dn not in todo:
                todo.append(dn)
    return chosen
