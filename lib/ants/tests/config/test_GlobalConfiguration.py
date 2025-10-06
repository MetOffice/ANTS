# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import copy
import io
import unittest.mock as mock

import ants.tests
from ants.config import GlobalConfiguration


def mock_config():
    config = copy.copy(GlobalConfiguration())
    config.__init__()

    target = {
        "ants_logging": {"enabled": None, "level": None},
        "ants_decomposition": {"x_split": None, "y_split": None, "pad_width": None},
        "ants_regridding_horizontal": {"extrapolation_mode": None, "scheme": None},
        "ants_regridding_vertical": {"extrapolation_mode": None, "scheme": None},
        "ants_metadata": {"history": None},
        "ants_tolerance": {"raymond_filter_isotropy_tolerance": None},
        "ants_tuning": {"disable_rechunking": None},
        "saver": None,
        "ants_fill": {"kdtree_latitude_scale": None},
    }
    return config, target


class Test___init__(ants.tests.TestCase):
    def test_default(self):
        config, target = mock_config()
        self.assertEqual(config.config, target)


class TestStr(ants.tests.TestCase):
    def test_all(self):
        config, target = mock_config()
        self.assertEqual(str(config), str(config))


class TestRepr(ants.tests.TestCase):
    def test_all(self):
        config, _ = mock_config()
        target = "GlobalConfiguration({})".format(repr(config.config))
        self.assertEqual(repr(config), target)


class TestGetItem(ants.tests.TestCase):
    def test_all(self):
        config, target = mock_config()
        self.assertEqual(config["ants_logging"], target["ants_logging"])


class TestLogger(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.config._initialise_logger")
        self.mock = patch.start()
        self.addCleanup(patch.stop)

    def test_parsed_logger(self):
        # Ensure that a logger is initialised when a logger name is parsed.
        data = "[ants_logging]\nlevel=5\nenabled=True"
        patch = mock.patch("ants.config.open", mock.mock_open(read_data=data))

        config, _ = mock_config()
        with patch:
            config.parse_configuration(mock.sentinel.fnme)
        self.mock.assert_called_once_with(level=5)


class TestParseConfiguration(ants.tests.TestCase):
    def test_dirty_header(self):
        # Ensure we support configuration files which have some information
        # within them which is outside the scope of a group.
        data = "somestuff\n[ants_metadata]\nhistory=foo"
        patch = mock.patch("ants.config.open", mock.mock_open(read_data=data))

        config, _ = mock_config()
        with patch:
            config.parse_configuration(mock.sentinel.fnme)
        self.assertEqual(config.config["ants_metadata"]["history"], "foo")

    def test_strict_parsing(self):
        # Config files with an ants prefixed group but not something we do
        # anything with in ANTS.
        data = "[ants_random]\nrandom=number"
        patch = mock.patch("ants.config.open", mock.mock_open(read_data=data))

        config, _ = mock_config()
        msg = 'The provided configuration section "ants_random" and '
        with self.assertRaisesRegex(KeyError, msg), patch:
            config.parse_configuration(mock.sentinel.fnme)

    @mock.patch("ants.config.open")
    def test_calls_set_temporary_directory(self, _):
        config, _ = mock_config()
        with mock.patch("ants.config.set_temporary_directory") as mock_call:
            config.parse_configuration("foo")
        mock_call.assert_called_once()


class TestGetOption(ants.tests.TestCase):
    def setUp(self):
        self.config, self.defaults = mock_config()
        sample = """[ants_logging]
level=WARNING
[ants_decomposition]
x_split=3 # some in-line comment
y_split=2
"""
        self.config._config.read_file(io.StringIO(sample))

    def test_with_comment(self):
        # Ensure that we support lines ending with Python comment '#'
        self.config._get_option("ants_decomposition", "x_split")
        self.assertEqual(self.config["ants_decomposition"]["x_split"], 3)

    def test_override(self):
        # Ensure that existing values are overridden by parsing multiple files.
        self.assertEqual(self.config["ants_logging"]["level"], None)
        self.config._get_option("ants_logging", "level")
        self.assertEqual(self.config["ants_logging"]["level"], "WARNING")

    def test_no_exist(self):
        # Ensure that we take the default value if there is no option to parse
        self.config._get_option("ants_logging", "enabled")
        self.assertEqual(
            self.config["ants_logging"]["enabled"],
            self.defaults["ants_logging"]["enabled"],
        )

    def test_parse_environmental_variables(self):
        patch = mock.patch("os.path.expandvars", side_effect=lambda x: x)
        with patch as mock_expandvars:
            self.config._get_option("ants_decomposition", "x_split")
        mock_expandvars.assert_called_once_with("3 # some in-line comment")


if __name__ == "__main__":
    ants.tests.main()
