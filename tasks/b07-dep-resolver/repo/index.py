class Index:
    """packages: {name: {version: {dependency_name: constraint}}}"""

    def __init__(self, packages):
        self._p = packages

    def versions(self, name):
        return list(self._p.get(name, {}))

    def deps(self, name, version):
        return dict(self._p[name][version])
