from bus import EventBus


def test_basic():
    b, got = EventBus(), []
    b.subscribe("t", got.append)
    assert b.publish("t", 1) == []
    assert got == [1]


def test_unsubscribe_during_dispatch_skips_nobody():
    b, calls = EventBus(), []
    unsub = None

    def once(p):
        calls.append("once")
        unsub()

    unsub = b.subscribe("t", once)
    b.subscribe("t", lambda p: calls.append("second"))
    b.publish("t")
    assert calls == ["once", "second"]
    b.publish("t")
    assert calls == ["once", "second", "second"]


def test_exception_isolated():
    b, calls = EventBus(), []

    def bad(p):
        raise RuntimeError("boom")

    b.subscribe("t", bad)
    b.subscribe("t", lambda p: calls.append("ok"))
    errs = b.publish("t")
    assert calls == ["ok"]
    assert len(errs) == 1 and isinstance(errs[0], RuntimeError)


def test_double_unsubscribe():
    b = EventBus()
    unsub = b.subscribe("t", lambda p: None)
    unsub()
    unsub()


def test_publish_unknown_topic():
    assert EventBus().publish("nope") == []
