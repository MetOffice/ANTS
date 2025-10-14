# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.decomposition
import ants.tests
from ants.decomposition import DomainDecompose


class Test_src_generator(ants.tests.TestCase):
    def test_illdefined_relationship_1src_ntgt_alt_grid(self):
        # Ensure that an exception is raised if we have multiple targets, 1
        # source, yet the targets are not on idential grids as each other.
        decom = DomainDecompose()
        msg = "Ill-defined relationship between 1 source and multiple targets"
        target1 = ants.tests.stock.geodetic((1, 1))
        target2 = ants.tests.stock.geodetic((1, 2))
        mosaics = [
            ants.decomposition.MosaicBySplit(tgt, (1, 1)) for tgt in [target1, target2]
        ]
        decom._mosaics = mosaics
        decom._sources = [mock.sentinel.source]
        with self.assertRaisesRegex(RuntimeError, msg):
            decom.src_generator

    def test_illdefined_relationship_nsrc_ntgt_ambiguous_pairing(self):
        # Ambiguous pairing between multiple sources and multiple targets as
        # their number is greater than 1 but their number do not match.
        decom = DomainDecompose()
        msg = "Ill-defined relationship between number of sources and targets"
        decom._mosaics = [
            mock.sentinel.target1,
            mock.sentinel.target2,
            mock.sentinel.target3,
        ]
        decom._sources = [mock.sentinel.source1, mock.sentinel.source2]
        with self.assertRaisesRegex(RuntimeError, msg):
            decom.src_generator


class Test_source_piece_generator(ants.tests.TestCase):
    def test_default_pad_width(self):
        """Test that the default pad_width of 1 is used in extraction."""
        global_cube = ants.tests.stock.geodetic((10, 10))
        decom = DomainDecompose()
        source = global_cube.copy()
        mosaic = [global_cube[:3], global_cube[3:6], global_cube[6:]]

        source_pieces = list(decom.source_piece_generator(source, mosaic))

        # A pad_width of 1 actually adds 2 rows of data beyond the target
        expected_source_pieces = [global_cube[:5], global_cube[1:8], global_cube[4:]]

        self.assertListEqual(source_pieces, expected_source_pieces)

    def test_pad_width_2(self):
        """Test that the a pad_width of 2 is used in extraction."""
        global_cube = ants.tests.stock.geodetic((10, 10))
        decom = DomainDecompose(pad_width=2)
        source = global_cube.copy()
        mosaic = [global_cube[:3], global_cube[3:6], global_cube[6:]]

        source_pieces = list(decom.source_piece_generator(source, mosaic))

        # A pad_width of 2 actually adds 3 rows of data beyond the target
        expected_source_pieces = [global_cube[:6], global_cube[:9], global_cube[3:]]

        self.assertListEqual(source_pieces, expected_source_pieces)


if __name__ == "__main__":
    ants.tests.main()
