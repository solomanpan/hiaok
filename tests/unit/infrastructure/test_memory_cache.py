import time


async def test_set_get_delete(cache):
    assert (await cache.get("k")).is_none()
    await cache.set("k", "v")
    assert (await cache.get("k")).value == "v"
    await cache.delete("k", "missing")
    assert (await cache.get("k")).is_none()


async def test_expired_entry_is_evicted(cache, monkeypatch):
    await cache.set("k", "v", ttl_seconds=1)
    later = time.monotonic() + 5
    monkeypatch.setattr(time, "monotonic", lambda: later)
    assert (await cache.get("k")).is_none()
