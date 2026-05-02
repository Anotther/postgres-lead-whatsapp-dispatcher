from lead_dispatcher import instance_pool
from lead_dispatcher.instance_pool import Instance, InstancePool


def test_get_available_instance_returns_none_when_all_are_delayed(monkeypatch):
    monkeypatch.setattr(instance_pool.time, "time", lambda: 100.0)
    pool = InstancePool(
        [
            Instance("caixa-01", 30, 90, next_available_at=101.0),
            Instance("caixa-02", 30, 90, next_available_at=102.0),
        ]
    )

    assert pool.get_available_instance() is None


def test_get_available_instance_balances_by_lowest_sent_count(monkeypatch):
    monkeypatch.setattr(instance_pool.time, "time", lambda: 100.0)
    least_used = Instance("caixa-02", 30, 90, sent_count=1)
    pool = InstancePool(
        [
            Instance("caixa-01", 30, 90, sent_count=3),
            least_used,
            Instance("caixa-03", 30, 90, next_available_at=101.0, sent_count=0),
        ]
    )

    assert pool.get_available_instance() is least_used


def test_mark_sent_sets_delay_and_increments_sent_count(monkeypatch):
    monkeypatch.setattr(instance_pool.time, "time", lambda: 100.0)
    monkeypatch.setattr(instance_pool.random, "randint", lambda minimum, maximum: 45)
    instance = Instance("caixa-01", 30, 90)
    pool = InstancePool([instance])

    pool.mark_sent(instance)

    assert instance.sent_count == 1
    assert instance.next_available_at == 145.0
