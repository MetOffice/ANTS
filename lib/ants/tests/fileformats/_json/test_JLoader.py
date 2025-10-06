# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
import numpy as np
from ants.fileformats.json import JSONLoader


class Test_load(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("json.load")
        self.jpatch = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("builtins.open")
        self.opatch = patch.start()
        self.addCleanup(patch.stop)

    def test_keys_case_insensitivity(self):
        # Check that keys which differ by only case are not differentiated.
        tar = {"key1": 1, "key2": 2}
        self.jpatch.return_value = tar
        loader = JSONLoader(keys=["key1", "KEY2"])
        res = loader.load(mock.sentinel.path)
        self.assertEqual(res, tar)

    def test_keys_duplicate(self):
        # Check that duplicate keys
        with self.assertRaisesRegex(ValueError, "Duplicate keys"):
            JSONLoader(keys=["key1", "key1"])

    def test_keys_duplicate_catch_alt_case(self):
        # Ensure we raise a suitable exception when duplicate keys are provide
        # which differ by case - as this could signify that the user wants
        # case sensitive usage (i.e. we don't want to silently continue in this
        # case).
        msg = r"Keys: \['key1', 'KEY1'\] appear to be case sensitive"
        with self.assertRaisesRegex(ValueError, msg):
            JSONLoader(keys=["key1", "KEY1"])

    def test_keys_alt_case(self):
        tar = {"key1": 1, "KEY1": 2}
        self.jpatch.return_value = tar
        loader = JSONLoader(keys=["key1", "KEY1"], case_sensitive=True)
        res = loader.load(mock.sentinel.path)
        self.assertEqual(res, tar)

    def test_case_insensitive_groups(self):
        tar = {"key1": 1, "KEY2": 2}
        self.jpatch.return_value = tar
        loader = JSONLoader(keys=["key1", "key2"])
        res = loader.load(mock.sentinel.path)
        self.assertEqual(res, {"key1": 1, "KEY2": 2})

    def test_open_provided_filepath(self):
        loader = JSONLoader()
        loader.load(mock.sentinel.path)

        self.opatch.assert_called_once_with(mock.sentinel.path, "r")

    def test_expected_keys(self):
        tar = {"key1": 1, "key2": 2}
        self.jpatch.return_value = tar
        loader = JSONLoader(keys=["key1", "key2"])
        res = loader.load(mock.sentinel.path)
        self.assertEqual(res, tar)

    def test_unexpected_keys(self):
        tar = {"key3": 3}
        self.jpatch.return_value = tar
        loader = JSONLoader(keys=["key1", "key2"])
        msg = "Keys: {'key[12]', 'key[12]'} missing from file"
        with self.assertRaisesRegex(KeyError, msg):
            loader.load(mock.sentinel.path)

    def test_ignore_unrequested_data(self):
        json = {"key1": 1, "key2": 2, "key3": 3}
        self.jpatch.return_value = json
        loader = JSONLoader(keys=["key1", "key2"])
        res = loader.load(mock.sentinel.path)
        tar = {"key1": 1, "key2": 2}
        self.assertEqual(res, tar)

    def test_no_requested_keys(self):
        tar = {"key1": 1, "key2": 2, "key3": 3}
        self.jpatch.return_value = tar
        loader = JSONLoader()
        res = loader.load(mock.sentinel.path)
        self.assertEqual(res, tar)

    def test_single_key(self):
        json = {"key1": 1, "key2": 2, "key3": 3}
        self.jpatch.return_value = json
        loader = JSONLoader(keys="key1")
        res = loader.load(mock.sentinel.path)
        tar = {"key1": 1}
        self.assertEqual(res, tar)

    def test_dtype_non_iterable(self):
        json = {"key1": 1}
        self.jpatch.return_value = json
        loader = JSONLoader(keys="key1", dtypes="int32")
        res = loader.load(mock.sentinel.path)
        tar = {"key1": np.int32(1)}
        self.assertEqual(res, tar)
        self.assertEqual(res["key1"].dtype, tar["key1"].dtype)

    def test_dtype_iterable(self):
        json = {"key1": [1, 2]}
        self.jpatch.return_value = json
        loader = JSONLoader(keys="key1", dtypes="int32")
        res = loader.load(mock.sentinel.path)
        tar = {"key1": np.array([1, 2], "int32")}
        self.assertArrayEqual(res["key1"], tar["key1"])
        self.assertEqual(res["key1"].dtype, tar["key1"].dtype)


if __name__ == "__main__":
    ants.tests.main()
