from defaults import DEFAULTS


def load(overrides=None):
    cfg = dict(DEFAULTS)
    cfg.update(overrides or {})
    return cfg
