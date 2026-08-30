# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Test battery for :func:`ants.decomposition.simple_split_and_process`.

These tests verify the fundamental correctness invariant: decomposing data into
N pieces and applying an operation to those pieces yields the same result as
applying the operation to the full dataset in a single pass (0 splits).

The test matrix covers:

  * Unary operations (single source, no target).
  * Binary operations (source + target) across a range of geographic domains:

    - Global coarse source -> global finer target.
    - Global coarse source -> UK regional target (straddles Greenwich Meridian).
    - Global coarse source -> Australia regional target (southern hemisphere).
    - Global coarse source -> New Zealand regional target (near International Dateline).
    - Global coarse source -> Singapore regional target (small equatorial domain).
    - Global coarse source -> Northern Greenland regional target (high latitude).
    - Global source with 0:360 longitude -> UK target with -180:180 longitude
      (tests coordinate convention mismatch handling).

Each test is parametrized over four split configurations:

  * (2, 2): 2 x-splits and 2 y-splits.
  * (3, 3): 3 x-splits and 3 y-splits.
  * (1, 4): 4 y-splits only (no x-splits).
  * (4, 1): 4 x-splits only (no y-splits).

The result with 0 splits (no decomposition) is used as the ground truth.
"""

import numpy
import numpy.testing
import pytest
import iris
import iris.analysis

import ants.decomposition
import ants.tests.stock as stock


# ---------------------------------------------------------------------------
# Split configurations to parametrize over: (number_of_x_splits, number_of_y_splits)
# The id string is used in the pytest output to identify each configuration.
# ---------------------------------------------------------------------------
SPLIT_CONFIGURATIONS = [
    pytest.param(2, 2, id="2x2_splits"),
    pytest.param(3, 3, id="3x3_splits"),
    pytest.param(1, 4, id="1x4_splits"),
    pytest.param(4, 1, id="4x1_splits"),
]

# Mixed longitude convention decomposition (for example, 0:360 source and
# -180:180 target) is expected to agree with the non-decomposed reference up
# to machine precision.  We enforce an explicit absolute tolerance here to
# avoid brittle exact-equality expectations in this numerically sensitive path.
MIXED_CONVENTION_ABSOLUTE_TOLERANCE = 1e-12


# ---------------------------------------------------------------------------
# Stock cube factory functions
#
# Source cubes are deliberately coarser than target cubes so that the linear
# regrid operation is a genuine interpolation rather than a trivial identity.
# All shapes are kept small (single-digit or low tens of cells per dimension)
# to keep the test suite fast.
# ---------------------------------------------------------------------------

def make_global_coarse_source():
    """
    Create a global coarse-resolution source cube using the -180:180 longitude
    convention.

    The cube covers the full globe at approximately 10-degree resolution
    (18 rows x 36 columns).  Data values are sequential integers, suitable
    for regridding tests.
    """
    return stock.geodetic(shape=(18, 36))


def make_global_coarse_source_0_to_360():
    """
    Create a global coarse-resolution source cube using the 0:360 longitude
    convention.

    Identical to :func:`make_global_coarse_source` except the x-coordinate
    spans 0 to 360 rather than -180 to 180.  Used to exercise coordinate
    convention mismatch between source and target during extraction.
    """
    return stock.geodetic(shape=(18, 36), xlim=(0, 360))


def make_global_fine_target():
    """
    Create a global fine-resolution target cube.

    The cube covers the full globe at approximately 5-degree resolution
    (9 rows x 18 columns), finer than the 10-degree source but still small
    enough for fast tests.
    """
    return stock.geodetic(shape=(9, 18))


def make_uk_target():
    """
    Create a target cube covering approximately the United Kingdom.

    The UK domain (49-61 N, -10 to 3 E) straddles the Greenwich Meridian.
    A 0:360-convention source must wrap around the 0/360 boundary to cover
    this region, making this an important test of extraction near zero longitude.
    """
    return stock.geodetic(shape=(6, 7), ylim=(49, 61), xlim=(-10, 3))


def make_australia_target():
    """
    Create a target cube covering approximately Australia.

    The domain (-45 to -10 N, 110 to 155 E) lies entirely in the southern
    hemisphere, well away from the wrap-around boundaries.  Both -180:180 and
    0:360 sources should yield this region without any wrapping.
    """
    return stock.geodetic(shape=(7, 9), ylim=(-45, -10), xlim=(110, 155))


def make_new_zealand_target():
    """
    Create a target cube covering approximately New Zealand.

    The domain (-48 to -33 N, 165 to 180 E) lies near the International
    Dateline at 180 degrees east.  This tests that extraction near the eastern
    edge of the common -180:180 longitude range is handled correctly.
    """
    return stock.geodetic(shape=(6, 6), ylim=(-48, -33), xlim=(165, 180))


def make_singapore_target():
    """
    Create a target cube covering approximately the Singapore region.

    The domain (1 to 2 N, 103 to 105 E) is a small equatorial region.  Used
    to verify that decomposition works correctly for small regional domains
    where individual split pieces may contain only 1 or 2 target grid cells.
    """
    return stock.geodetic(shape=(4, 4), ylim=(1, 2), xlim=(103, 105))


def make_northern_greenland_target():
    """
    Create a target cube covering approximately northern Greenland.

    The domain (75 to 85 N, -75 to -15 E) is at high latitude.  Used to
    verify that y-splitting behaves correctly in polar regions where grid
    cells are narrow in the x-direction relative to their geographic extent.
    """
    return stock.geodetic(shape=(4, 12), ylim=(75, 85), xlim=(-75, -15))


# ---------------------------------------------------------------------------
# Operations used in tests
# ---------------------------------------------------------------------------

def add_one_to_source(source):
    """Unary operation: add 1.0 to every data value in the source cube."""
    return source + 1


def regrid_source_to_target(source, target):
    """
    Binary operation: regrid the source cube onto the target grid using
    iris linear interpolation.

    :func:`iris.analysis.Linear` is used as a representative, well-understood
    binary operation for validating the decomposition framework.
    """
    return source.regrid(target, iris.analysis.Linear())


def regrid_source_to_target_areaweighted(source, target):
    """
    Binary operation: regrid the source cube onto the target grid using
    iris area-weighted interpolation.

    This operation is sensitive to small target tiles that can collapse a
    singleton horizontal dimension in intermediate pieces, so it is used to
    validate decomposition piece-shape conformity before concatenation.
    """
    return source.regrid(target, iris.analysis.AreaWeighted())


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

def assert_decomposed_result_matches_reference(actual, expected):
    """
    Assert that a decomposed result matches the reference (0-splits) result.

    Checks:

    * Data values are numerically equal within floating-point tolerance.
    * Data dtype is identical.
    * Cube metadata (name, units, coordinates) is identical.

    Parameters
    ----------
    actual : :class:`iris.cube.Cube`
        Result obtained by running with N splits.
    expected : :class:`iris.cube.Cube`
        Reference result obtained by running with 0 splits.
    """
    numpy.testing.assert_array_almost_equal(
        actual.data,
        expected.data,
        err_msg=(
            "Data values differ between the decomposed result and the "
            "reference (0-splits) result."
        ),
    )
    assert actual.data.dtype == expected.data.dtype, (
        f"dtype mismatch: decomposed result has dtype {actual.data.dtype!r}, "
        f"but reference result has dtype {expected.data.dtype!r}."
    )
    assert actual.metadata == expected.metadata, (
        f"Cube metadata mismatch:\n"
        f"  actual:   {actual.metadata}\n"
        f"  expected: {expected.metadata}"
    )


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("number_of_x_splits,number_of_y_splits", SPLIT_CONFIGURATIONS)
class TestUnaryOperation:
    """
    Tests that unary operations produce identical results with and without
    splitting.

    A unary operation takes only a source cube and returns a result cube.
    The source is split into pieces, the operation applied to each piece, and
    the pieces reassembled.
    """

    def test_global_domain(self, number_of_x_splits, number_of_y_splits):
        """
        Unary operation on a global coarse-resolution source should give the
        same result whether run with 0 splits or N splits.
        """
        source = make_global_coarse_source()
        reference_result = ants.decomposition.simple_split_and_process(
            add_one_to_source,
            source,
        )
        decomposed_result = ants.decomposition.simple_split_and_process(
            add_one_to_source,
            source,
            number_of_x_splits=number_of_x_splits,
            number_of_y_splits=number_of_y_splits,
        )
        assert_decomposed_result_matches_reference(decomposed_result, reference_result)


@pytest.mark.parametrize("number_of_x_splits,number_of_y_splits", SPLIT_CONFIGURATIONS)
class TestBinaryOperation:
    """
    Tests that binary operations (source regridded to target) produce identical
    results with and without splitting, across a range of geographic domains.

    A binary operation takes a source cube and a target cube.  In the
    decomposed case the *target* is split into pieces, the source region
    overlapping each target piece is extracted, the operation applied to each
    (source piece, target piece) pair, and the results reassembled.
    """

    def _run_binary_test(self, source, target, number_of_x_splits, number_of_y_splits):
        """
        Run the binary operation with 0 splits (reference) and with the given
        split configuration, returning both results.

        Parameters
        ----------
        source : :class:`iris.cube.Cube`
        target : :class:`iris.cube.Cube`
        number_of_x_splits : int
        number_of_y_splits : int

        Returns
        -------
        decomposed_result : :class:`iris.cube.Cube`
        reference_result : :class:`iris.cube.Cube`
        """
        reference_result = ants.decomposition.simple_split_and_process(
            regrid_source_to_target,
            source,
            target=target,
        )
        decomposed_result = ants.decomposition.simple_split_and_process(
            regrid_source_to_target,
            source,
            target=target,
            number_of_x_splits=number_of_x_splits,
            number_of_y_splits=number_of_y_splits,
        )
        return decomposed_result, reference_result

    def test_global_source_global_fine_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        """
        Binary operation: global coarse source -> global fine target.

        Tests that the decomposition preserves results for a straightforward
        global-to-global regrid with no regional or wrap-around complications.
        """
        source = make_global_coarse_source()
        target = make_global_fine_target()
        decomposed, reference = self._run_binary_test(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)


    def test_global_source_uk_target(self, number_of_x_splits, number_of_y_splits):
        """
        Binary operation: global coarse source -> UK regional target.

        The UK domain straddles the Greenwich Meridian (-10 to 3 E).
        A -180:180 source must provide cells from both sides of 0 degrees.
        """
        source = make_global_coarse_source()
        target = make_uk_target()
        decomposed, reference = self._run_binary_test(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)
    def test_global_source_australia_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        """
        Binary operation: global coarse source -> Australia regional target.

        The domain is in the southern hemisphere (negative latitudes) and
        entirely within a single contiguous longitude range with no wrapping
        required.
        """
        source = make_global_coarse_source()
        target = make_australia_target()
        decomposed, reference = self._run_binary_test(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)
    def test_global_source_new_zealand_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        """
        Binary operation: global coarse source -> New Zealand target.

        The domain sits near the International Dateline (165 to 180 E).
        This tests correct handling of the eastern edge of the standard
        -180:180 longitude range.
        """
        source = make_global_coarse_source()
        target = make_new_zealand_target()
        decomposed, reference = self._run_binary_test(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)

    def test_global_source_singapore_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        """
        Binary operation: global coarse source -> Singapore regional target.

        A small (4x4 cell) equatorial domain.  With larger split counts some
        individual target pieces will contain only 1 or 2 cells, exercising
        the behaviour of iris linear regrid on very small sub-domains.
        """
        source = make_global_coarse_source()
        target = make_singapore_target()
        decomposed, reference = self._run_binary_test(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)

    def test_global_source_northern_greenland_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        """
        Binary operation: global coarse source -> Northern Greenland target.

        A high-latitude domain (75 to 85 N).  Tests that y-splitting near the
        poles does not introduce numerical differences.
        """
        source = make_global_coarse_source()
        target = make_northern_greenland_target()
        decomposed, reference = self._run_binary_test(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)

    def test_global_0_to_360_source_regional_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        """
        Binary operation: global 0:360 longitude source -> UK -180:180 target.

        Tests that the source region extraction correctly handles the case
        where source and target use different x-coordinate conventions.  The
        UK target (−10 to 3 E) requires the 0:360 source to provide cells
        from near 350-360 degrees, which must be re-mapped to the target's
        negative-longitude range for iris to interpolate correctly.
        """
        source = make_global_coarse_source_0_to_360()
        target = make_uk_target()
        decomposed, reference = self._run_binary_test(
            source, target, number_of_x_splits, number_of_y_splits
        )
        numpy.testing.assert_allclose(
            decomposed.data,
            reference.data,
            rtol=0.0,
            atol=MIXED_CONVENTION_ABSOLUTE_TOLERANCE,
            err_msg=(
                "Mixed longitude convention decomposition exceeded expected "
                "machine-precision tolerance relative to the non-decomposed "
                "reference."
            ),
        )
        assert decomposed.data.dtype == reference.data.dtype, (
            f"dtype mismatch: decomposed result has dtype {decomposed.data.dtype!r}, "
            f"but reference result has dtype {reference.data.dtype!r}."
        )
        assert decomposed.metadata == reference.metadata, (
            f"Cube metadata mismatch:\n"
            f"  decomposed: {decomposed.metadata}\n"
            f"  reference:  {reference.metadata}"
        )


class TestConcatenateResultPiecesRegression:
    """Regression tests for _ssp_concatenate_result_pieces dtype handling."""

    def test_mixed_piece_dtypes_promoted_to_common_dtype(self):
        """
        Mixed integer/float piece dtypes are promoted before concatenation.

        This protects against regressions in the final dtype guard path used
        when assembling binary operation piece results.
        """
        cube = stock.geodetic(shape=(6, 8))
        piece_left = cube[:, :4].copy()
        piece_right = cube[:, 4:].copy()

        piece_left.data = piece_left.data.astype(numpy.int32)
        piece_right.data = piece_right.data.astype(numpy.float64)

        expected_dtype = numpy.result_type(piece_left.dtype, piece_right.dtype)
        assembled = ants.decomposition._ssp_concatenate_result_pieces(
            [piece_left, piece_right]
        )

        assert assembled.dtype == expected_dtype
        numpy.testing.assert_array_equal(
            assembled.data,
            cube.data.astype(expected_dtype),
        )


@pytest.mark.parametrize("number_of_x_splits,number_of_y_splits", SPLIT_CONFIGURATIONS)
class TestBinaryOperationAreaWeighted:
    """
    Tests that area-weighted binary operations produce stable decomposed
    results across supported domain/split combinations.
    """

    def _run_binary_test_areaweighted(
        self, source, target, number_of_x_splits, number_of_y_splits
    ):
        reference_result = ants.decomposition.simple_split_and_process(
            regrid_source_to_target_areaweighted,
            source,
            target=target,
        )
        decomposed_result = ants.decomposition.simple_split_and_process(
            regrid_source_to_target_areaweighted,
            source,
            target=target,
            number_of_x_splits=number_of_x_splits,
            number_of_y_splits=number_of_y_splits,
        )
        return decomposed_result, reference_result

    def test_global_source_global_fine_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        source = make_global_coarse_source()
        target = make_global_fine_target()
        decomposed, reference = self._run_binary_test_areaweighted(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)

    def test_global_source_uk_target(self, number_of_x_splits, number_of_y_splits):
        source = make_global_coarse_source()
        target = make_uk_target()
        decomposed, reference = self._run_binary_test_areaweighted(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)

    def test_global_source_australia_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        source = make_global_coarse_source()
        target = make_australia_target()
        decomposed, reference = self._run_binary_test_areaweighted(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)

    def test_global_source_new_zealand_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        source = make_global_coarse_source()
        target = make_new_zealand_target()
        decomposed, reference = self._run_binary_test_areaweighted(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)

    def test_global_source_singapore_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        source = make_global_coarse_source()
        target = make_singapore_target()
        decomposed, reference = self._run_binary_test_areaweighted(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)

    def test_global_source_northern_greenland_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        source = make_global_coarse_source()
        target = make_northern_greenland_target()
        decomposed, reference = self._run_binary_test_areaweighted(
            source, target, number_of_x_splits, number_of_y_splits
        )
        assert_decomposed_result_matches_reference(decomposed, reference)

    def test_global_0_to_360_source_regional_target(
        self, number_of_x_splits, number_of_y_splits
    ):
        source = make_global_coarse_source_0_to_360()
        target = make_uk_target()
        decomposed, reference = self._run_binary_test_areaweighted(
            source, target, number_of_x_splits, number_of_y_splits
        )
        numpy.testing.assert_allclose(
            decomposed.data,
            reference.data,
            rtol=0.0,
            atol=MIXED_CONVENTION_ABSOLUTE_TOLERANCE,
            err_msg=(
                "Mixed longitude convention area-weighted decomposition "
                "exceeded expected machine-precision tolerance."
            ),
        )
        assert decomposed.data.dtype == reference.data.dtype
        assert decomposed.metadata == reference.metadata
