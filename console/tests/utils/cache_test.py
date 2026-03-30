# coding: utf-8
from unittest import TestCase, mock

import os

from console.utils.cache import Cache


class CacheMemoryTests(TestCase):
    # capability_id: console.cache.memory-store-and-expire
    def test_memory_cache_returns_value_before_expiration(self):
        cache = Cache(max_cache_size=2)
        with mock.patch("console.utils.cache.time.time", return_value=100):
            cache.set("foo", "bar", 30)
        with mock.patch("console.utils.cache.time.time", return_value=120):
            self.assertEqual(cache.get("foo"), "bar")

    # capability_id: console.cache.expired-eviction
    def test_memory_cache_evicts_expired_entry_on_get(self):
        cache = Cache(max_cache_size=2)
        with mock.patch("console.utils.cache.time.time", return_value=100):
            cache.set("foo", "bar", 10)
        with mock.patch("console.utils.cache.time.time", return_value=111):
            self.assertIsNone(cache.get("foo"))
        self.assertEqual(cache.size, 0)

    # capability_id: console.cache.capacity-guard
    def test_memory_cache_refuses_new_key_when_full_without_expired_entries(self):
        cache = Cache(max_cache_size=1)
        with mock.patch("console.utils.cache.time.time", return_value=100):
            cache.set("foo", "bar", 30)
        with mock.patch("console.utils.cache.time.time", return_value=101):
            cache.set("baz", "qux", 30)
            self.assertEqual(cache.get("foo"), "bar")
            self.assertIsNone(cache.get("baz"))

    # capability_id: console.cache.capacity-guard
    def test_memory_cache_reuses_expired_slot_when_full(self):
        cache = Cache(max_cache_size=1)
        with mock.patch("console.utils.cache.time.time", return_value=100):
            cache.set("foo", "bar", 1)
        with mock.patch("console.utils.cache.time.time", return_value=102):
            cache.set("baz", "qux", 30)
            self.assertIsNone(cache.get("foo"))
            self.assertEqual(cache.get("baz"), "qux")

    # capability_id: console.cache.update-existing-at-capacity
    def test_memory_cache_updates_existing_key_when_full(self):
        cache = Cache(max_cache_size=1)
        with mock.patch("console.utils.cache.time.time", return_value=100):
            cache.set("foo", "bar", 30)
        with mock.patch("console.utils.cache.time.time", return_value=101):
            cache.set("foo", "baz", 30)
            self.assertEqual(cache.get("foo"), "baz")

    # capability_id: console.cache.expired-eviction-count
    def test_remove_expired_key_returns_removed_count(self):
        cache = Cache(max_cache_size=3)
        with mock.patch("console.utils.cache.time.time", return_value=100):
            cache.set("foo", "bar", 1)
            cache.set("baz", "qux", 30)
        with mock.patch("console.utils.cache.time.time", return_value=102):
            self.assertEqual(cache._remove_expired_key(), 1)
            self.assertNotIn("foo", cache.cache)
            self.assertIn("baz", cache.cache)

    # capability_id: console.cache.redis-enabled-flag
    def test_enable_redis_follows_env(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(Cache().enable_redis)
        with mock.patch.dict(os.environ, {"REDIS_HOST": "127.0.0.1"}, clear=True):
            self.assertTrue(Cache().enable_redis)

    # capability_id: console.cache.redis-client-config
    def test_cache_initializes_redis_client_from_env(self):
        with mock.patch.dict(os.environ, {
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "REDIS_DB": "2",
            "REDIS_PASSWORD": "secret",
        }, clear=True):
            with mock.patch("console.utils.cache.redis.Redis") as mock_redis:
                Cache()
                mock_redis.assert_called_once_with(
                    host="redis.example.com",
                    port="6380",
                    db="2",
                    password="secret",
                )

    # capability_id: console.cache.redis-backend-read-write
    def test_cache_delegates_get_and_set_to_redis_backend(self):
        with mock.patch.dict(os.environ, {"REDIS_HOST": "redis.example.com"}, clear=True):
            redis_client = mock.Mock()
            redis_client.get.return_value = "value"
            with mock.patch("console.utils.cache.redis.Redis", return_value=redis_client):
                cache = Cache()
                self.assertEqual(cache.get("foo"), "value")
                cache.set("foo", "bar", 30)
                redis_client.get.assert_called_once_with("foo")
                redis_client.set.assert_called_once_with("foo", "bar", 30)

    # capability_id: console.cache.redis-read-error
    def test_redis_get_swallow_exception(self):
        with mock.patch.dict(os.environ, {"REDIS_HOST": "redis.example.com"}, clear=True):
            redis_client = mock.Mock()
            redis_client.get.side_effect = Exception("boom")
            with mock.patch("console.utils.cache.redis.Redis", return_value=redis_client):
                cache = Cache()
                self.assertIsNone(cache.get("foo"))

    # capability_id: console.cache.redis-write-error
    def test_redis_set_swallow_exception(self):
        with mock.patch.dict(os.environ, {"REDIS_HOST": "redis.example.com"}, clear=True):
            redis_client = mock.Mock()
            redis_client.set.side_effect = Exception("boom")
            with mock.patch("console.utils.cache.redis.Redis", return_value=redis_client):
                cache = Cache()
                self.assertIsNone(cache.set("foo", "bar", 30))
