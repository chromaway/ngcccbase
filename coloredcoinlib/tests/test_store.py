#!/usr/bin/env python

import os
import unittest

from coloredcoinlib.store import (DataStoreConnection, ColorDataStore,
                                  ColorMetaStore, PersistentDictStore)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.dsc = DataStoreConnection(":memory:")
        self.store = ColorDataStore(self.dsc.conn)
        self.persistent = PersistentDictStore(self.dsc.conn, 'per')
        self.meta = ColorMetaStore(self.dsc.conn)

    def test_autocommit(self):
        path = "/tmp/tmp.db"
        c = DataStoreConnection(path, True)
        self.assertFalse(c.conn.isolation_level)
        os.remove(path)

    def test_table_exists(self):
        self.assertFalse(self.store.table_exists('notthere'))

    def test_sync(self):
        self.assertFalse(self.store.sync())

    def test_transaction(self):
        self.assertEqual(self.store.transaction(), self.dsc.conn)

    def test_colordata(self):
        self.assertFalse(self.store.get(1, "1", 0))
        self.assertFalse(self.store.get_any("1", 0))
        self.assertFalse(self.store.get_all(1))
        self.store.add(1, "1", 0, 1, "test0")
        self.assertTrue(self.store.get(1, "1", 0))
        self.assertTrue(self.store.get_any("1", 0))
        self.assertTrue(self.store.get_all(1))
        self.store.remove(1, "1", 0)
        self.assertFalse(self.store.get(1, "1", 0))
        self.assertFalse(self.store.get_any("1", 0))
        self.assertFalse(self.store.get_all(1))

    def test_persistent(self):
        self.assertFalse(self.persistent.get("tmp"))
        self.persistent['tmp'] = 1
        self.assertTrue(self.persistent.get("tmp"))
        self.assertEqual(self.persistent.keys(), ['tmp'])
        del self.persistent['tmp']
        self.assertFalse(self.persistent.get("tmp"))
        self.assertRaises(KeyError, self.persistent.__delitem__, 'tmp')

    def test_meta(self):
        self.assertFalse(self.meta.did_scan(1, "hash"))
        self.meta.set_as_scanned(1, "hash")
        self.assertTrue(self.meta.did_scan(1, "hash"))
        self.assertFalse(self.meta.find_color_desc(1))
        self.meta.resolve_color_desc("color", True)
        self.assertTrue(self.meta.find_color_desc(1))


if __name__ == '__main__':
    unittest.main()
