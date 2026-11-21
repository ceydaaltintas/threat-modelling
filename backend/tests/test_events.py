"""The event broker feeds the live stepper; late subscribers must catch up."""

from __future__ import annotations

from app.core.events import EventBroker


async def test_subscriber_receives_published_event() -> None:
    broker = EventBroker()
    queue, backlog = await broker.subscribe("run-1")
    assert backlog == []

    await broker.publish("run-1", {"type": "step", "step": 1, "status": "running"})
    event = await queue.get()

    assert event["run_id"] == "run-1"
    assert event["step"] == 1
    assert "ts" in event


async def test_late_subscriber_gets_the_backlog_in_order() -> None:
    broker = EventBroker()
    for no in (1, 2, 3):
        await broker.publish("run-2", {"type": "step", "step": no})

    _, backlog = await broker.subscribe("run-2")
    assert [e["step"] for e in backlog] == [1, 2, 3]


async def test_events_are_isolated_per_run() -> None:
    broker = EventBroker()
    queue, _ = await broker.subscribe("run-a")
    await broker.publish("run-b", {"type": "step", "step": 1})

    assert queue.empty()


async def test_unsubscribe_stops_delivery() -> None:
    broker = EventBroker()
    queue, _ = await broker.subscribe("run-c")
    await broker.unsubscribe("run-c", queue)
    await broker.publish("run-c", {"type": "step", "step": 1})

    assert queue.empty()
