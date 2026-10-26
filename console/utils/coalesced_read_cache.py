# -*- coding: utf-8 -*-
import copy
import threading
import time


class CoalescedReadCache(object):
    """Process-local TTL cache sharing only simultaneous reads of the same key."""

    def __init__(self):
        self._entries = {}
        self._flights = {}
        self._generation = 0
        self._lock = threading.Lock()

    def clear(self):
        with self._lock:
            self._generation += 1
            self._entries.clear()
            # Existing readers may finish, but subsequent readers start a new flight.
            self._flights.clear()

    def get(self, key, ttl, loader, now=None):
        if ttl <= 0:
            return copy.deepcopy(loader())

        started = time.monotonic()
        read_time = started if now is None else now
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] > read_time:
                cached = entry[1]
                flight = None
                leader = False
            else:
                cached = None
                flight = self._flights.get(key)
                leader = flight is None
                if leader:
                    flight = {"event": threading.Event(), "generation": self._generation, "value": None, "error": None}
                    self._flights[key] = flight

        if flight is None:
            return copy.deepcopy(cached)
        if not leader:
            flight["event"].wait()
            if flight["error"] is not None:
                raise flight["error"]
            return copy.deepcopy(flight["value"])

        try:
            value = copy.deepcopy(loader())
            completed = time.monotonic()
            # Preserve the explicit clock override used by deterministic TTL callers.
            expires_at = (completed if now is None else now + completed - started) + ttl
            with self._lock:
                flight["value"] = value
                if flight["generation"] == self._generation:
                    self._entries[key] = (expires_at, value)
        except BaseException as error:
            flight["error"] = error
            raise
        finally:
            with self._lock:
                if self._flights.get(key) is flight:
                    del self._flights[key]
            flight["event"].set()
        return copy.deepcopy(value)
