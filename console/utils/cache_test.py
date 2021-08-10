# -*- coding: utf8 -*-
import time
import unittest

from cache import Cache


class MyTestCase(unittest.TestCase):
    def test_set_and_get(self):
        cache = Cache()
        test_keys = ["key1", "key2", "key3"]
        for key in test_keys:
            cache.set(key, "{} value".format(key), 2)
        for key in test_keys:
            if cache.enable_redis:
                self.assertEqual(cache.get(key).decode('UTF-8'), "{} value".format(key))
                continue
            self.assertEqual(cache.get(key), "{} value".format(key))

    def test_cache_exceeds_max_size(self):
        cache = Cache(2)
        if cache.enable_redis:
            return
        test_keys = ["key1", "key2", "key3"]
        for key in test_keys:
            cache.set(key, "{} value".format(key), 2)
        for key in test_keys:
            if key == "key3":
                self.assertEqual(cache.get(key), None)
                continue
            self.assertEqual(cache.get(key), "{} value".format(key))

    def test_remove_expired_keys(self):
        cache = Cache(2)
        test_keys = ["key1", "key2", "key3"]
        for key in test_keys:
            cache.set(key, "{} value".format(key), 2)
        time.sleep(2)
        for key in test_keys:
            if cache.enable_redis:
                self.assertEqual(cache.get(key), None)
                continue
            if key != "key3":
                continue
            self.assertEqual(cache.size, 2)
            cache.set(key, "key3 value", 2)
            self.assertEqual(cache.size, 1)
            self.assertEqual(cache.get(key), "key3 value")


if __name__ == '__main__':
    unittest.main()
