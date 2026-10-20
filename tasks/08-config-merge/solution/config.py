import copy
from defaults import DEFAULTS


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def load(overrides=None):
    return _merge(copy.deepcopy(DEFAULTS), overrides or {})
