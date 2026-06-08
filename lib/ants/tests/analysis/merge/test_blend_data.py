# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import numpy as np
import pytest
from ants.analysis._merge import blend_data


class TestExceptions:
    def test_invalid_blending_distance_0(self):
        source1 = np.array([0])
        source2 = np.array([0])
        mask = np.array([0])
        blending_distance = 0
        expected_msg = "Invalid blending_distance: 0. Must be greater than zero"
        with pytest.raises(ValueError, match=expected_msg):
            blend_data(source1, source2, mask, blending_distance)

    def test_blending_distance_too_large(self):
        source1 = np.zeros((10, 10))
        source2 = np.ones_like(source1)
        mask = source1.copy()
        blending_distance = 6
        expected_msg = (
            "Invalid blending_distance=6: greater than half the domain size "
            r"\(shape=\(10, 10\)\)"
        )
        with pytest.raises(ValueError, match=expected_msg):
            blend_data(source1, source2, mask, blending_distance)

    def test_1D_fails(self):
        source1 = np.zeros(3)
        source2 = np.ones_like(source1)
        mask = source1.copy()
        blending_distance = 2
        expected_msg = "Can only blend 2-dimensional data, got data with 1 dimensions"
        with pytest.raises(ValueError, match=expected_msg):
            blend_data(source1, source2, mask, blending_distance)

    def test_3D_fails(self):
        source1 = np.zeros((3, 3, 3))
        source2 = np.ones_like(source1)
        mask = source1.copy()
        blending_distance = 2
        expected_msg = "Can only blend 2-dimensional data, got data with 3 dimensions"
        with pytest.raises(ValueError, match=expected_msg):
            blend_data(source1, source2, mask, blending_distance)

    def test_different_source_shapes(self):
        source1 = np.zeros((2, 3))
        source2 = np.ones((3, 2))
        mask = np.ones_like(source1, dtype=bool)
        blending_distance = 1

        expected_msg = (
            r"Cannot blend sources with different shapes: \(2, 3\) and \(3, 2\)"
        )
        with pytest.raises(ValueError, match=expected_msg):
            blend_data(source1, source2, mask, blending_distance)

    def test_different_source_and_mask_shapes(self):
        source1 = np.zeros((2, 3))
        source2 = np.ones_like(source1)
        mask = np.ones((3, 2), dtype=bool)
        blending_distance = 1

        expected_msg = (
            "Cannot blend sources as mask shape is inconsistent with source shape. "
            r"Source shape: \(2, 3\), Mask shape: \(3, 2\)"
        )
        with pytest.raises(ValueError, match=expected_msg):
            blend_data(source1, source2, mask, blending_distance)

    def test_blending_covers_entire_region(self):
        source1 = np.zeros((5, 5))
        source2 = np.ones_like(source1)
        mask = np.array(
            [
                [0, 0, 0, 0, 0],
                [0, 1, 1, 1, 0],
                [0, 1, 1, 1, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
            ],
            dtype=bool,
        )
        blending_distance = 2.0
        expected_msg = (
            "All points within the region are within the blending distance. "
            "Specified blending_distance=2.0, maximum distance into domain: 1.0"
        )
        with pytest.warns(match=expected_msg):
            blend_data(source1, source2, mask, blending_distance)


class TestFunctionality:
    @pytest.fixture()
    def source1(self):
        return np.zeros((7, 7), dtype=np.float64)

    @pytest.fixture()
    def source2(self):
        return np.ones((7, 7), dtype=np.float64)

    @pytest.fixture()
    def mask(self):
        mask = np.array(
            [
                [1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 0, 0, 1, 1],
                [1, 1, 1, 0, 0, 0, 1],
                [1, 1, 1, 0, 0, 0, 0],
                [1, 1, 1, 0, 0, 0, 0],
            ],
            dtype=bool,
        )
        return mask

    def test_blending_2D(self, source1, source2, mask):
        blending_distance = 2.5

        expected = np.array(
            [
                [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                [1.0, 1.0, 0.89442719, 0.8, 0.8, 0.89442719, 1.0],
                [1.0, 0.89442719, 0.56568542, 0.4, 0.4, 0.56568542, 0.89442719],
                [1.0, 0.8, 0.4, 0.0, 0.0, 0.4, 0.56568542],
                [1.0, 0.8, 0.4, 0.0, 0.0, 0.0, 0.4],
                [1.0, 0.8, 0.4, 0.0, 0.0, 0.0, 0.0],
                [1.0, 0.8, 0.4, 0.0, 0.0, 0.0, 0.0],
            ]
        )

        blended = blend_data(source1, source2, mask, blending_distance)

        np.testing.assert_array_almost_equal(blended, expected)

    def test_blending_2D_circular(self, source1, source2, mask):
        blending_distance = 2.5

        expected = np.array(
            [
                [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                [1.0, 1.0, 0.89442719, 0.8, 0.8, 0.89442719, 1.0],
                [1.0, 0.89442719, 0.56568542, 0.4, 0.4, 0.56568542, 0.89442719],
                [0.89442719, 0.8, 0.4, 0.0, 0.0, 0.4, 0.56568542],
                [0.56568542, 0.8, 0.4, 0.0, 0.0, 0.0, 0.4],
                [0.4, 0.8, 0.4, 0.0, 0.0, 0.0, 0.0],
                [0.4, 0.8, 0.4, 0.0, 0.0, 0.0, 0.0],
            ]
        )

        blended = blend_data(source1, source2, mask, blending_distance, circular=True)

        np.testing.assert_array_almost_equal(blended, expected)
