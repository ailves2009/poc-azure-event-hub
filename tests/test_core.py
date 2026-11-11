from core import build_orders, compute_lag, group_by_key, kafka_settings, signals


def test_orders_are_reproducible_and_unique():
    a = build_orders(100, 10, seed=42)
    assert a == build_orders(100, 10, seed=42)
    assert len({o["message_id"] for o in a}) == 100


def test_group_by_key_keeps_send_order_per_customer():
    orders = build_orders(200, 5, seed=1)
    for customer, group in group_by_key(orders).items():
        assert all(o["customer_id"] == customer for o in group)
        ids = [o["order_id"] for o in group]
        assert ids == sorted(ids)


def test_lag_with_and_without_checkpoint():
    lags = {p.partition_id: p for p in compute_lag({"0": 99, "1": 9, "2": -1}, {"0": 99, "1": 4})}
    assert lags["0"].lag == 0  # fully processed
    assert lags["1"].lag == 5  # 5..9 not processed
    assert lags["2"].lag == 0  # empty partition, no checkpoint


def test_never_checkpointed_partition_counts_everything():
    (p,) = compute_lag({"0": 9}, {})
    assert p.lag == 10 and p.checkpoint is None


def test_partitions_sorted_numerically():
    ids = [p.partition_id for p in compute_lag({"10": 0, "2": 0, "1": 0}, {})]
    assert ids == ["1", "2", "10"]


def test_signals_healthy():
    lags = compute_lag({"0": 9, "1": 9}, {"0": 9, "1": 9})
    s = signals(lags, {"IncomingMessages": 600}, throughput_units=1, window_sec=3600)
    assert not s["consumer_behind"] and not s["throttled"] and not s["near_capacity"]


def test_signals_hot_partition_and_throttling():
    lags = compute_lag({"0": 999, "1": 9, "2": 9, "3": 9}, {"0": 0, "1": 9, "2": 9, "3": 9})
    s = signals(lags, {"ThrottledRequests": 3, "IncomingMessages": 3_000_000}, 1, 3600)
    assert s["hot_partition"] and s["throttled"] and s["near_capacity"]


def test_kafka_settings_use_entra_id_not_passwords():
    cfg = kafka_settings("evhns-x.servicebus.windows.net", "orders-kafka")
    assert cfg["bootstrap.servers"] == "evhns-x.servicebus.windows.net:9093"
    assert cfg["security.protocol"] == "SASL_SSL"
    assert cfg["sasl.mechanism"] == "OAUTHBEARER"
    assert not any("password" in k or "username" in k for k in cfg)
