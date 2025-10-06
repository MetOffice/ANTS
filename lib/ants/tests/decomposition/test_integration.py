# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Integration tests for all decomposition frameworks.

All operations must be defined in global scope for them to be pickleable (i.e.
suitable for multiprocessing or any parallelism framework).

"""
import os
import unittest.mock as mock

import ants.decomposition as decomp
import ants.tests
import iris
from ants.utils.cube import as_cubelist
from iris.analysis import Linear


def unary(source):
    return source + 1


def unary_multi_source(sources):
    return sources[0] + sources[1]


def unary_multi_source_multi_return(sources):
    expected_cube_list = iris.cube.CubeList()
    expected_cube_list.append(sources[0])
    expected_cube_list.append(sources[1])
    return expected_cube_list


def binary(source, target):
    expected_cube = source.regrid(target, Linear())
    return expected_cube


def binary_multi_return(source, target):
    expected_cube_list = iris.cube.CubeList()
    mean = source.regrid(target, Linear())
    standard_deviation = mean.copy()
    mean.rename("mean")
    standard_deviation.rename("standard_deviation")
    expected_cube_list.append(mean)
    expected_cube_list.append(standard_deviation)
    return expected_cube_list


def binary_multi_source_multi_return(sources, targets):
    expected_cube_list = iris.cube.CubeList()
    expected_cube_list.append(sources[0].regrid(targets, Linear()))
    expected_cube_list.append(sources[1].regrid(targets, Linear()))
    return expected_cube_list


def binary_multi_source_multi_target(sources, targets):
    expected_cube_list = iris.cube.CubeList()
    result1 = sources[0].regrid(targets[0], Linear())
    result2 = sources[1].regrid(targets[1], Linear())
    result1.rename(targets[0].name())
    result2.rename(targets[1].name())
    expected_cube_list.append(result1)
    expected_cube_list.append(result2)
    return expected_cube_list


def binary_single_source_multi_target(source, targets):
    expected_cube_list = iris.cube.CubeList()
    result1 = source.regrid(targets[0], Linear())
    result2 = source.regrid(targets[1], Linear())
    result1.rename(targets[0].name())
    result2.rename(targets[1].name())
    expected_cube_list.append(result1)
    expected_cube_list.append(result2)
    return expected_cube_list


def _unary_setup():
    source1 = ants.tests.stock.geodetic((4, 4))
    source1.rename("ret1")
    mosaic1 = decomp.MosaicBySplit(source1, (2, 1))
    source2 = source1.copy()
    source2.rename("ret2")
    mosaic2 = decomp.MosaicBySplit(source2, (2, 1))
    return [source1, source2], [mosaic1, mosaic2]


def _binary_setup():
    targets, mosaics = _unary_setup()
    source1 = ants.tests.stock.geodetic((4, 4))
    source1.rename("src1")
    source2 = source1.copy()
    source2.rename("src2")
    return [source1, source2], targets, mosaics


class Common(object):
    def setUp(self):
        patch = mock.patch("warnings.warn")
        self.mock_warnings = patch.start()
        self.addCleanup(patch.stop)

    def _assert_metadata_equal(self, actual_results, expected_results):
        for result, expected in zip(
            as_cubelist(actual_results), as_cubelist(expected_results)
        ):
            self.assertEqual(result.metadata, expected.metadata)

    def _assert_types_equal(self, actual_results, expected_results):
        self.assertEqual(type(actual_results), type(expected_results))

    def _assert_data_equal(self, actual_results, expected_results):
        for result, expected in zip(
            as_cubelist(actual_results), as_cubelist(expected_results)
        ):
            self.assertArrayEqual(result.data, expected.data)

    def _assert_cube_data_array_types_equal(self, actual_results, expected_results):
        for result, expected in zip(
            as_cubelist(actual_results), as_cubelist(expected_results)
        ):
            self.assertEqual(type(result.data), type(expected.data))

    def test_unary(self):
        sources, mosaics = _unary_setup()
        result = self.decomposition_framework(unary, mosaics[0])
        expected = unary(sources[0])
        expected = ants.utils.cube.defer_cube(expected)
        self._assert_cube_data_array_types_equal(result, expected)
        self._assert_metadata_equal(result, expected)
        self._assert_types_equal(result, expected)
        self._assert_data_equal(result, expected)

    def test_unary_multiple_source_single_return(self):
        sources, mosaics = _unary_setup()
        result = self.decomposition_framework(unary_multi_source, mosaics)
        expected = unary_multi_source(sources)
        expected = ants.utils.cube.defer_cube(expected)
        self._assert_cube_data_array_types_equal(result, expected)
        self._assert_metadata_equal(result, expected)
        self._assert_types_equal(result, expected)
        self._assert_data_equal(result, expected)

    def test_unary_multiple_source_multi_return(self):
        sources, mosaics = _unary_setup()
        results = self.decomposition_framework(unary_multi_source_multi_return, mosaics)
        expected = unary_multi_source_multi_return(sources)
        expected = ants.utils.cube.defer_cube(expected)
        self._assert_cube_data_array_types_equal(results, expected)
        self._assert_metadata_equal(results, expected)
        self._assert_types_equal(results, expected)
        self._assert_data_equal(results, expected)

    def test_binary(self):
        # Single source, single expected
        sources, targets, mosaics = _binary_setup()
        result = self.decomposition_framework(binary, mosaics[0], sources[0])
        expected = binary(sources[0], targets[0])
        expected = ants.utils.cube.defer_cube(expected)
        self._assert_cube_data_array_types_equal(result, expected)
        self._assert_metadata_equal(result, expected)
        self._assert_types_equal(result, expected)
        self._assert_data_equal(result, expected)

    def test_binary_multi_return(self):
        # Binary operations utilise extract overlap and return more than one
        # cube.  Real examples include mean and standard_deviation returns.
        sources, targets, mosaics = _binary_setup()
        results = self.decomposition_framework(
            binary_multi_return, mosaics[0], sources[0]
        )
        expected = binary_multi_return(sources[0], targets[0])
        expected = ants.utils.cube.defer_cube(expected)
        self._assert_cube_data_array_types_equal(results, expected)
        self._assert_metadata_equal(results, expected)
        self._assert_types_equal(results, expected)
        self._assert_data_equal(results, expected)

    def test_binary_multi_source_multi_return(self):
        sources, targets, mosaics = _binary_setup()
        results = self.decomposition_framework(
            binary_multi_source_multi_return, mosaics[0], sources
        )
        expected = binary_multi_source_multi_return(sources, targets[0])
        expected = ants.utils.cube.defer_cube(expected)
        self._assert_cube_data_array_types_equal(results, expected)
        self._assert_metadata_equal(results, expected)
        self._assert_types_equal(results, expected)
        self._assert_data_equal(results, expected)

    def test_binary_multi_source_multi_target(self):
        sources, targets, mosaics = _binary_setup()
        results = self.decomposition_framework(
            binary_multi_source_multi_target, mosaics, sources
        )
        expected = binary_multi_source_multi_target(sources, targets)
        expected = ants.utils.cube.defer_cube(expected)
        self._assert_cube_data_array_types_equal(results, expected)
        self._assert_metadata_equal(results, expected)
        self._assert_types_equal(results, expected)
        self._assert_data_equal(results, expected)

    def test_binary_single_source_multi_target(self):
        sources, targets, mosaics = _binary_setup()
        results = self.decomposition_framework(
            binary_single_source_multi_target, mosaics, sources[0]
        )
        expected = binary_single_source_multi_target(sources[0], targets)
        expected = ants.utils.cube.defer_cube(expected)
        self._assert_cube_data_array_types_equal(results, expected)
        self._assert_metadata_equal(results, expected)
        self._assert_types_equal(results, expected)
        self._assert_data_equal(results, expected)


class TestMultiprocessingDomainDecompose(Common, ants.tests.TestCase):
    decomposition_framework = decomp.MultiprocessingDomainDecompose()

    def setUp(self):
        super().setUp()
        os.environ["ANTS_NPROCESSES"] = str(2)


class TestDomainDecompose(Common, ants.tests.TestCase):
    decomposition_framework = decomp.DomainDecompose()


if __name__ == "__main__":
    ants.tests.main()
