"""Background tasks say what went wrong, and caches stay bounded."""

import asyncio

import pytest

from app import push, tmdb


def test_the_reminder_task_logs_errors_and_carries_on(monkeypatch, caplog):
    def kaputt(db):
        raise RuntimeError("boom")

    runden = []

    async def schlafen(_):
        runden.append(1)
        if len(runden) == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(push, "faellige_erinnerungen", kaputt)
    monkeypatch.setattr(push.asyncio, "sleep", schlafen)
    with caplog.at_level("ERROR"), pytest.raises(asyncio.CancelledError):
        asyncio.run(push.erinnern())
    assert len(runden) == 2  # it went on after the first failure
    assert caplog.text.count("Push reminders failed") == 2 and "boom" in caplog.text


def test_the_tmdb_cache_stays_bounded(monkeypatch):
    monkeypatch.setattr(tmdb, "CACHE_MAX", 10)
    tmdb._cache.clear()

    async def fuellen():
        for i in range(25):
            await tmdb._cached(f"k{i}", 3600, lambda i=i: _wert(i))

    async def _wert(i):
        return i

    asyncio.run(fuellen())
    assert len(tmdb._cache) <= 10
    assert "k24" in tmdb._cache  # the newest stays
    tmdb._cache.clear()
