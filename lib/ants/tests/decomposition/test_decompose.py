# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import copy
import unittest.mock as mock

import ants.tests
from ants.decomposition import decompose


class TestAll(ants.tests.TestCase):
    def setUp(self):
        split = {"split_x": 3, "split_y": 2}
        patch = mock.patch("ants.decomposition._guess_split", return_value=split)
        self.split = (2, 3)
        self.mock__guess_split = patch.start()
        self.addCleanup(patch.stop)

        # Make an empty CONFIG to ensure that the tests are not sensitive to
        # configuration files.
        new_config = copy.copy(ants.config.GlobalConfiguration())
        new_config.__init__()

        patch = mock.patch("ants.decomposition.CONFIG", new=new_config)
        self.mock_config = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch(
            "ants.decomposition.MosaicBySplit", return_value=mock.sentinel.mosaic
        )
        self.mock_split = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.decomposition.DomainDecompose")
        self.decomposer = patch.start()
        self.addCleanup(patch.stop)

        self.cube = ants.tests.stock.geodetic((2, 2), name="source")

    @mock.patch("ants.utils.cube.defer_cube")
    def test_default_args(self, *args):
        # Ensure we pass the underlying functions to which we depend the
        # arguments we expect and in the correct order.
        operator = mock.Mock()
        decompose(operator, self.cube)
        self.decomposer().assert_not_called()
        self.mock_split.assert_not_called()
        operator.assert_called_once_with(self.cube)

    @mock.patch("ants.utils.cube.defer_cube")
    def test_default_args_with_target(self, *args):
        # Ensure we pass arguments in the expected order for the underlying
        # functions.
        operator = mock.Mock()
        target = ants.tests.stock.geodetic((2, 2), name="target")
        decompose(operator, self.cube, target)
        self.decomposer().assert_not_called()
        self.mock_split.assert_not_called()
        operator.assert_called_once_with(self.cube, target)

    def test_only_x_split_automatic(self):
        # Test that an error is raised if only one of the splits is set to be guessed.
        self.mock_config["ants_decomposition"]["x_split"] = "automatic"
        self.mock_config["ants_decomposition"]["y_split"] = 5
        msg = "If either x_split or y_split is set to automatic, both must be."
        with self.assertRaisesRegex(RuntimeError, msg):
            decompose(mock.sentinel.operator, self.cube)

    def test_only_y_split_automatic(self):
        # Test that an error is raised if only one of the splits is set to be guessed.
        self.mock_config["ants_decomposition"]["y_split"] = "automatic"
        self.mock_config["ants_decomposition"]["x_split"] = 5
        msg = "If either x_split or y_split is set to automatic, both must be."
        with self.assertRaisesRegex(RuntimeError, msg):
            decompose(mock.sentinel.operator, self.cube)

    def test_only_x_split_0(self):
        # Test that an error is raised if only one of the splits is set to 0.
        self.mock_config["ants_decomposition"]["x_split"] = 0
        self.mock_config["ants_decomposition"]["y_split"] = 5
        msg = "If either x_split or y_split is set to 0, both must be."
        with self.assertRaisesRegex(RuntimeError, msg):
            decompose(mock.sentinel.operator, self.cube)

    def test_only_y_split_0(self):
        # Test that an error is raised if only one of the splits is set to 0.
        self.mock_config["ants_decomposition"]["y_split"] = 0
        self.mock_config["ants_decomposition"]["x_split"] = 2
        msg = "If either x_split or y_split is set to 0, both must be."
        with self.assertRaisesRegex(RuntimeError, msg):
            decompose(mock.sentinel.operator, self.cube)

    def test_only_y_split_set(self):
        # Test that an error is raised if only one of the splits is set by the user.
        self.mock_config["ants_decomposition"]["y_split"] = 0
        msg = "If either x_split or y_split is set, both must be."
        with self.assertRaisesRegex(RuntimeError, msg):
            decompose(mock.sentinel.operator, self.cube)

    def test_only_x_split_set(self):
        # Test that an error is raised if only one of the splits is set by the user.
        self.mock_config["ants_decomposition"]["x_split"] = 2
        msg = "If either x_split or y_split is set, both must be."
        with self.assertRaisesRegex(RuntimeError, msg):
            decompose(mock.sentinel.operator, self.cube)

    def test_override_split_config(self):
        # Override parameter from the ants.config.CONFIG
        self.mock_config["ants_decomposition"]["x_split"] = 6
        self.mock_config["ants_decomposition"]["y_split"] = 5
        split = (5, 6)
        decompose(mock.sentinel.operator, self.cube)
        self.mock_split.assert_called_once_with(self.cube, split)

    def test_xy_split(self):
        cube = ants.tests.stock.geodetic((5, 6, 12, 8))
        self.mock_config["ants_decomposition"]["x_split"] = 2
        self.mock_config["ants_decomposition"]["y_split"] = 3
        decompose(mock.sentinel.operator, cube)
        res = self.mock_split.call_args[0]
        tar = [cube, (1, 1, 3, 2)]
        self.assertIs(res[0], tar[0])
        self.assertArrayEqual(res[1], tar[1])

    def test_xy_split_targets_provided(self):
        # Ensure that the split is correctly derived from using the target
        # cube(s).  We pass an iterable of 1 to check this.
        source = ants.tests.stock.geodetic((12, 8))
        target = [ants.tests.stock.geodetic((5, 6, 12, 8))]
        self.mock_config["ants_decomposition"]["x_split"] = 2
        self.mock_config["ants_decomposition"]["y_split"] = 3
        decompose(mock.sentinel.operator, source, target)
        res = self.mock_split.call_args[0]
        self.assertArrayEqual(res[1], (1, 1, 3, 2))

    def test_requested_processes_user_scheduler_collision(self):
        # User specifying 'processes' when using a scheduler should cause a
        # collision (we should ALWAYS respect scheduler parameters).
        env = {"SLURM_NTASKS": "3", "ANTS_NPROCESSES": "10"}
        patch = mock.patch("os.getenv", side_effect=lambda x, y: env.get(x, y))
        msg = "Decomposition configuration overspecified"
        with patch, self.assertRaisesRegex(ValueError, msg):
            decompose(mock.sentinel.operator, self.cube)

    @mock.patch("ants.utils.cube.defer_cube")
    def test_no_decomposition(self, *args):
        # Ensure decomposition is not called if specified x and y splits are 0.
        self.mock_config["ants_decomposition"]["x_split"] = 0
        self.mock_config["ants_decomposition"]["y_split"] = 0
        operator = mock.Mock()
        decompose(operator, self.cube)
        self.decomposer().assert_not_called()
        self.mock_split.assert_not_called()
        operator.assert_called_once_with(self.cube)

    def test_decomposition_with_1x1_split(self, *args):
        # Ensure decomposition is called if specified x and y splits are 1.
        self.mock_config["ants_decomposition"]["x_split"] = 1
        self.mock_config["ants_decomposition"]["y_split"] = 1
        split = (1, 1)
        decompose(mock.sentinel.operator, self.cube)
        self.mock_split.assert_called_once_with(self.cube, split)
        self.decomposer().assert_called_once_with(
            mock.sentinel.operator, mock.sentinel.mosaic
        )

    def test_decomposition_with_no_x_split(self):
        # Ensure decomposition is called if x split is 1 but y split is larger.
        self.mock_config["ants_decomposition"]["x_split"] = 1
        self.mock_config["ants_decomposition"]["y_split"] = 2
        split = (2, 1)
        decompose(mock.sentinel.operator, self.cube)
        self.mock_split.assert_called_once_with(self.cube, split)
        self.decomposer().assert_called_once_with(
            mock.sentinel.operator, mock.sentinel.mosaic
        )

    def test_decomposition_with_no_y_split(self):
        # Ensure decomposition is called if y split is 1 but x split is larger.
        self.mock_config["ants_decomposition"]["x_split"] = 2
        self.mock_config["ants_decomposition"]["y_split"] = 1
        split = (1, 2)
        decompose(mock.sentinel.operator, self.cube)
        self.mock_split.assert_called_once_with(self.cube, split)
        self.decomposer().assert_called_once_with(
            mock.sentinel.operator, mock.sentinel.mosaic
        )

    @mock.patch("ants.utils.cube.defer_cube")
    def test_no_decomposition_with_target(self, *args):
        # Ensure we pass arguments in the expected order for the underlying
        # functions if decomposition is not called.
        self.mock_config["ants_decomposition"]["x_split"] = 0
        self.mock_config["ants_decomposition"]["y_split"] = 0
        operator = mock.Mock()
        target = ants.tests.stock.geodetic((2, 2), name="target")
        decompose(operator, self.cube, target)
        self.decomposer().assert_not_called()
        self.mock_split.assert_not_called()
        operator.assert_called_once_with(self.cube, target)

    def test_automatic_splits(self):
        # Ensure we pass the underlying functions to which we depend the
        # arguments we expect and in the correct order when automatic splits are used.
        self.mock_config["ants_decomposition"]["x_split"] = "automatic"
        self.mock_config["ants_decomposition"]["y_split"] = "automatic"
        decompose(mock.sentinel.operator, self.cube)
        self.mock_split.assert_called_once_with(self.cube, self.split)
        self.decomposer().assert_called_once_with(
            mock.sentinel.operator, mock.sentinel.mosaic
        )

    def test_automatic_splits_with_target(self):
        # Ensure we pass the underlying functions to which we depend the
        # arguments we expect and in the correct order when automatic splits are uesd.
        self.mock_config["ants_decomposition"]["x_split"] = "automatic"
        self.mock_config["ants_decomposition"]["y_split"] = "automatic"
        target = ants.tests.stock.geodetic((2, 2), name="target")
        decompose(mock.sentinel.operator, self.cube, target)
        self.mock_split.assert_called_once_with(target, self.split)
        self.decomposer().assert_called_once_with(
            mock.sentinel.operator, mock.sentinel.mosaic, self.cube
        )

    def test_pad_width_config_None(self):
        """Test that the pad_width set in the config is passed to the decomposition.

        In this case, use the default config setting of None, so the pad_width
        passed should be 1."""
        # Set splits to automatic to force the decomposition to use the mosaics
        self.mock_config["ants_decomposition"]["x_split"] = "automatic"
        self.mock_config["ants_decomposition"]["y_split"] = "automatic"

        # This is the default pad_width config
        self.mock_config["ants_decomposition"]["pad_width"] = None
        target = ants.tests.stock.geodetic((2, 2), name="target")
        decompose(mock.sentinel.operator, self.cube, target)

        # DomainDecompose should have been initialised with a pad_width of 1
        self.decomposer.assert_called_once_with(pad_width=1)

    def test_pad_width_config_2(self):
        """Test that the pad_width set in the config is passed to the decomposition.

        In this case, use a non-default config setting of 2, so the pad_width
        passed should be 2."""
        # Set splits to automatic to force the decomposition to use the mosaics
        self.mock_config["ants_decomposition"]["x_split"] = "automatic"
        self.mock_config["ants_decomposition"]["y_split"] = "automatic"

        self.mock_config["ants_decomposition"]["pad_width"] = 2
        target = ants.tests.stock.geodetic((2, 2), name="target")
        decompose(mock.sentinel.operator, self.cube, target)

        # DomainDecompose should have been initialised with a pad_width of 2
        self.decomposer.assert_called_once_with(pad_width=2)


if __name__ == "__main__":
    ants.tests.main()
