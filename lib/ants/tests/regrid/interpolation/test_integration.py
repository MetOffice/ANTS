# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock
from functools import partial

import ants.regrid.interpolation as interpolation
import ants.tests
import ants.tests.stock as stock
import iris
import numpy as np
import pytest
import stratify


def stub_relevel(*args, **kwargs):
    return args[0]


class _Common:
    """
    Vertical coordinates, multidimensional with broadcasting.

    Source::

    air_temperature / (K)               (time: 1; model_level_number: 4; \
            latitude: 5; longitude: 6)
         Dimension coordinates:
              time                           x                      -    \
                      -             -
              model_level_number             -                      x    \
                      -             -
              latitude                       -                      -    \
                      x             -
              longitude                      -                      -    \
                      -             x
         Auxiliary coordinates:
              level_height                   -                      x    \
                      -             -
              sigma                          -                      x    \
                      -             -
              surface_altitude               -                      -    \
                      x             x
         Derived coordinates:
              altitude                       -                      x    \
                      x             x

    Target::

    air_temperature / (K)               (model_level_number: 4; latitude: 5; \
            longitude: 6)
         Dimension coordinates:
              model_level_number                           x            -    \
                      -
              latitude                                     -            x    \
                      -
              longitude                                    -            -    \
                      x
         Auxiliary coordinates:
              level_height                                 x            -    \
                      -
              sigma                                        x            -    \
                      -
              surface_altitude                             -            x    \
                      x
         Derived coordinates:
              altitude                                     x            x    \
                      x
         Scalar coordinates:
              time: 1970-01-01 00:00:00

    """

    def setUp(self):
        self.source = stock.simple_4d_with_hybrid_height()[0:1]
        ants.utils.cube.set_crs(self.source, ants.coord_systems.UM_SPHERE)
        ants.utils.cube.guess_horizontal_bounds(self.source)
        self.target = self.source.copy()[0]

        lh_coord = self.target.coord("level_height")
        lh_coord.points = lh_coord.points + 0.5
        lh_coord = self.source.coord("time")
        lh_coord.points = lh_coord.points + 10


@ants.tests.skip_stratify
class TestAll(_Common, ants.tests.TestCase):
    def test_no_vertical_grid(self):
        # Ensure that not having any vertical coordinates doesn't cause a
        # failure.
        source = stock.geodetic((2, 2))
        target = source.copy()
        patch_relevel = mock.patch(
            "ants.regrid.interpolation._relevel", side_effect=stub_relevel
        )
        with patch_relevel as patched_relevel:
            res = source.regrid(target, interpolation.Linear())

        self.assertIs(res, source)
        self.assertFalse(patched_relevel.called)

    def test_eq_2d_relevel_not_called(self):
        # Let's make the source vertical coordinates horizontal to the target.
        self.source.coord("level_height").points = self.target.coord(
            "level_height"
        ).points
        patch_relevel = mock.patch(
            "ants.regrid.interpolation._relevel", side_effect=stub_relevel
        )
        with patch_relevel as patched_relevel:
            res = self.source.regrid(self.target, interpolation.Linear())

        self.assertIs(res, self.source)
        self.assertFalse(patched_relevel.called)

    def assert_relevel_called_with(self, scheme, interpolator):
        patch_relevel = mock.patch(
            "ants.regrid.interpolation._relevel", side_effect=stub_relevel
        )
        with patch_relevel as patched_relevel:
            res = self.source.regrid(self.target, scheme)

        self.assertEqual(res, self.source)
        self.assertEqual(patched_relevel.call_args[0][0], self.source)
        self.assertEqual(patched_relevel.call_args[0][1], self.source.coord("altitude"))
        self.assertArrayEqual(
            patched_relevel.call_args[0][2], self.target.coord("altitude"), 1
        )
        self.assertEqual(
            patched_relevel.call_args[0][3].keywords, interpolator.keywords
        )

    def test_neq_2d_alt_length_relevel_linear_called(self):
        # Ensure relevel is called when the source and target altitude length
        # differs.
        self.source = self.source[:, 1:]
        scheme = interpolation.Linear()
        interpolator = partial(
            stratify.interpolate, interpolation="linear", extrapolation="linear"
        )
        self.assert_relevel_called_with(scheme, interpolator)

    def test_neq_2d_relevel_linear_called(self):
        scheme = interpolation.Linear()
        interpolator = partial(
            stratify.interpolate, interpolation="linear", extrapolation="linear"
        )
        self.assert_relevel_called_with(scheme, interpolator)

    def test_neq_2d_relevel_nearest_called(self):
        scheme = interpolation.Nearest()
        interpolator = partial(
            stratify.interpolate, interpolation="nearest", extrapolation="nearest"
        )
        self.assert_relevel_called_with(scheme, interpolator)

    def test_neq_2d_mapping_return_cube(self):
        """
        Ensure expected usage where the target dimension mapping does not
        match the source.  This checks that the result in based on the ordering
        of the source AND that the results are independent of the target
        ordering.

        Source:
            (time: 1; model_level_number: 4; latitude: 5; longitude: 6)
        Target:
            (latitude: 5; model_level_number: 4; longitude: 6)

        """
        res = self.source.regrid(self.target, interpolation.Linear())
        self.target.transpose((1, 0, 2))
        res2 = self.source.regrid(self.target, interpolation.Linear())
        self.assertEqual(res, res2)

        self.source.transpose((3, 1, 0, 2))
        res3 = self.source.regrid(self.target, interpolation.Linear())
        res3.transpose((2, 1, 3, 0))
        ants.utils.cube.sanitise_auxcoords(res3)
        self.assertEqual(res3, res2)

    def test_neq_1d_returned_values_sanity_check(self):
        """
        Ensure that the values returned are as expected i.e. sanity check that
        linear interpolation is actually occurring.

        """
        self.source.remove_aux_factory(self.source.aux_factories[0])
        self.target.remove_aux_factory(self.target.aux_factories[0])
        self.target = self.target[:3]
        res = self.source.regrid(self.target, interpolation.Linear())

        # Interpolation points (target levels) are half way between the source
        # levels and so are easily testable as follows:
        self.assertArrayAlmostEqual(
            res.data, (self.source[:, 1:].data + self.source[:, :-1].data) / 2.0
        )

    def test_no_src_aux_factory_tgt_aux_factory(self):
        """
        Ensure that the result doesn't end up with coordinates from the target
        aux factory where we don't have one in the source (that is, where we
        perform level_heights -> level_heights interpolation).

        """
        self.source.remove_aux_factory(self.source.aux_factories[0])
        self.target = self.target[:3]
        res = self.source.regrid(self.target, interpolation.Linear())
        self.assertEqual(len(res.aux_factories), 0)
        self.assertEqual(len(res.coords("altitude")), 0)

    def test_neq_1d_alternate_ordering_return_cube(self):
        """
        Ensure expected usage where the target dimension ordering does not
        match the source.

        """
        # Remove altitude to simplify the testcase.
        self.source.remove_aux_factory(self.source.aux_factories[0])
        self.target.remove_aux_factory(self.target.aux_factories[0])

        res = self.source.regrid(self.target, interpolation.Linear())

        coord_names = ["model_level_number", "level_height", "sigma"]
        for coord_name in coord_names:
            coord = self.target.coord(coord_name)
            coord.points = coord.points.copy()[::-1]
        res2 = self.source.regrid(self.target, interpolation.Linear())
        self.assertEqual(res, res2)

    def test_1d_unequal_horizontal_grid(self):
        """
        Ensure that we can vertically regrid the source to a target even if
        the two are defined on different horizontal domains AS LONG AS the
        vertical coordinate does not vary over the horizontal domain, i.e.
        a vertical coordinate such as level_height which is not a function of
        x and y.

        See TestExceptions.test_unequal_horizontal_grid for the failing case
        where the vertical coordinate is a function of x and y with different
        horizontal domains between source and target.

        """
        # Remove altitiude as it varies with x and y
        self.source.remove_aux_factory(self.source.aux_factories[0])
        self.target.remove_aux_factory(self.target.aux_factories[0])

        # Vertically regrid with identical horizontal grids.
        res1 = self.source.regrid(self.target, interpolation.Linear())

        # Vertically regrid with differing horizontal grids.
        points = self.source.coord(axis="x").points.copy()
        points += 1
        self.source.coord(axis="x").points = points
        res2 = self.source.regrid(self.target, interpolation.Linear())
        self.assertArrayAlmostEqual(res1.data, res2.data)

    def test_1d_alternative_units(self):
        # Check that having different units between the source and target is
        # supported and that the units of the result is taken from the target,
        # since that defines the 'target grid'.
        # Remove altitude as it varies with x and y
        self.source.remove_aux_factory(self.source.aux_factories[0])
        self.target.remove_aux_factory(self.target.aux_factories[0])

        # Vertically regrid with identical horizontal grids.
        res1 = self.source.regrid(self.target, interpolation.Linear())

        self.target.coord("level_height").convert_units("km")
        res2 = self.source.regrid(self.target, interpolation.Linear())

        self.assertArrayAlmostEqual(res1.data, res2.data)
        self.assertEqual(res2.coord("level_height").units, "km")

    def test_target_interpolation_coord_as_aux_coord(self):
        # Ensure we do not promote the interpolation coordinate to a dimension
        # coordinate if the target grid doesn't define it as such.  This
        # ensures we don't end up with model level numbers as an aux coord and
        # level heights as dim coords for example.

        # To test this, we setup the interpolation coordinate to meet the
        # conditions to be made a dimension coordinate (monotonically
        # increasing).  We then check that it doesn't inadvertently get made
        # a dimension coordinate.
        # We remove the hybrid factory to make setting this test up easier -
        # making altitude monotonically increasing would be more laborious
        # given that it's a derived coordinate.
        self.source.remove_aux_factory(self.source.aux_factories[0])
        self.target.remove_aux_factory(self.target.aux_factories[0])
        res = self.source.regrid(self.target, interpolation.Linear())
        self.assertTrue(len(res.coords("model_level_number", dim_coords=True)) > 0)


class TestCoordinates(_Common):
    # This class deliberately does not inherit from ants.tests.TestCase.  This
    # means we can use pytest parametrize.
    @pytest.mark.parametrize(
        "name",
        [
            ("model_level_number"),
            ("latitude"),
            ("longitude"),
            ("level_height"),
            ("sigma"),
            ("surface_altitude"),
            ("altitude"),
        ],
    )
    def test_neq_2d_return_coordinates(self, name):
        """Ensure that all the spatial coordinates on the result are correct.

        Correct in this case means the same as on the target."""
        self.setUp()  # Needed because this class is not a unittest.TestCase.
        expected = self.target.coord(name)

        result = self.source.regrid(self.target, interpolation.Linear())
        actual = result.coord(name)

        assert actual == expected


@ants.tests.skip_stratify
class TestConservative(ants.tests.TestCase):
    def setUp(self):
        self.source = stock.simple_4d_with_hybrid_height()[0:1]
        self.source.coord("level_height").guess_bounds()
        ants.utils.cube.set_crs(self.source, ants.coord_systems.UM_SPHERE)
        ants.utils.cube.guess_horizontal_bounds(self.source)
        self.target = self.source.copy()[0]
        self.source = self.source[:, :2]

    def test_interpolator_api(self):
        patch_interpolator = mock.patch(
            "ants.regrid.interpolation.StratifyInterpolator"
        )
        with patch_interpolator as patched_interpolator:
            self.source.regrid(self.target, interpolation.Conservative())
        patched_interpolator.assert_called_once_with(
            self.source, self.target, stratify.interpolate_conservative
        )

    def test_conservative_stratify_api(self):
        ret_shape = list(self.source.shape)
        ret_shape[1] = self.target.shape[0]
        ret_data = np.zeros(ret_shape)

        patch_stratify = mock.patch(
            "ants.regrid.interpolation.stratify.interpolate_conservative",
            return_value=ret_data,
            __name__="interpolate_conservative",
        )
        with patch_stratify as patched_stratify:
            self.source.regrid(self.target, interpolation.Conservative())
        self.assertArrayEqual(
            patched_stratify.call_args[0][0], self.target.coord("altitude").bounds
        )
        self.assertArrayEqual(
            patched_stratify.call_args[0][1], self.source.coord("altitude").bounds
        )
        self.assertArrayEqual(patched_stratify.call_args[0][2], self.source.data)
        self.assertArrayEqual(patched_stratify.call_args[1], {"axis": 1})
        self.assertEqual(len(patched_stratify.call_args[0]), 3)
        self.assertEqual(len(patched_stratify.call_args[1]), 1)

    def test_value(self):
        res = self.source.regrid(self.target, interpolation.Conservative())
        target = np.empty(self.target.shape)
        target.fill(np.nan)
        target[:2] = self.source.data[:]
        self.assertArrayEqual(
            res.data[np.logical_not(np.isnan(res.data))],
            target[np.logical_not(np.isnan(target))],
        )

    def test_bounds_preserved(self):
        # Ensure that the bounds are actually preserved on the returned cube.
        res = self.source.regrid(self.target, interpolation.Conservative())
        self.assertArrayEqual(
            res.coord("altitude").bounds, self.target.coord("altitude").bounds
        )

    def test_no_bounds(self):
        self.source.coord("level_height").bounds = None
        msg = 'Source coord "altitude" does not have bounds.'
        with self.assertRaisesRegex(ValueError, msg):
            self.source.regrid(self.target, interpolation.Conservative())


@ants.tests.skip_stratify
class TestExceptions(ants.tests.TestCase):
    def test_incompatible_source_target(self):
        # Used to ensure consistent vertical coordinate ordering between source
        # and target.
        # Ensure that we fall over when the dimensionality of the source and
        # target definition are not identical
        source = stock.simple_4d_with_hybrid_height()
        target = stock.simple_4d_with_hybrid_height()[:, 0]
        msg = (
            "Expecting the source and target vertical grid to vary over "
            "the same number of dimensions"
        )
        with self.assertRaisesRegex(RuntimeError, msg):
            source.regrid(target, interpolation.Linear())

    def test_non_rectilinear_dimensions(self):
        # Used to ensure consistent vertical coordinate ordering between source
        # and target.
        # Ensure that all coordinates other than the one used for
        # interpolation is rectilinear for the vertical grid definition.
        # Not imposing this restriction would make the reordering a
        # multidimensional problem which is expensive, complex and
        # unnecessary with our current usecases.
        source = stock.simple_4d_with_hybrid_height()
        target = stock.simple_4d_with_hybrid_height()
        coord = source.coord(axis="x")
        source.remove_coord(coord)
        source.add_aux_coord(coord, 3)
        msg = "Expecting common dimension coordinates between both"
        with self.assertRaisesRegex(RuntimeError, msg):
            source.regrid(target, interpolation.Linear())

    def test_uncommon_coordinates(self):
        # Used to ensure consistent vertical coordinate ordering between source
        # and target.
        # Ensure common coordinates between the vertical grid definition of the
        # source and target to allow us to determine the order using these
        # coordinates.
        source = stock.simple_4d_with_hybrid_height()
        target = stock.simple_4d_with_hybrid_height()
        coord = source.coord(axis="x")
        coord.rename("projection_x")
        msg = "Expecting common dimension coordinates between both"
        with self.assertRaisesRegex(RuntimeError, msg):
            source.regrid(target, interpolation.Linear())

    def test_unequal_surface_coordinates(self):
        # Raise an exception where the surface coordinates do not agree.
        source = stock.simple_4d_with_hybrid_height()
        target = stock.simple_4d_with_hybrid_height()
        coord = source.coord("surface_altitude")
        coord.points = coord.points + 1
        msg = "The surface_altitude coordinate of source and target do not " "agree"
        with self.assertRaisesRegex(RuntimeError, msg):
            source.regrid(target, interpolation.Linear())

    def test_2d_unequal_horizontal_grid(self):
        # Raise an exception when z(y, x) such as the altitude coordinate but
        # the horizontal grid of source and target are not identical.
        # see TestAll.test_unequal_horizontal_grid for the unambiguous case we
        # accept.
        source = stock.simple_4d_with_hybrid_height()
        target = stock.simple_4d_with_hybrid_height()
        coord = source.coord(axis="x")
        coord.points = coord.points + 1
        msg = "The longitude coordinate of source and target do not agree"
        with self.assertRaisesRegex(RuntimeError, msg):
            source.regrid(target, interpolation.Linear())

    def test_multiple_axes_of_interpolation(self):
        # Check a suitable exception is raised when there is more than one axis
        # of interpolation.
        source = stock.simple_4d_with_hybrid_height()
        target = stock.simple_4d_with_hybrid_height()

        lh_coord = source.coord("level_height")
        lhs_coord = iris.coords.DimCoord.from_coord(lh_coord)
        source.aux_factories[0].update(lh_coord, lhs_coord)

        lh_coord = target.coord("level_height")
        lht_coord = iris.coords.DimCoord.from_coord(lh_coord)
        points = lh_coord.points + 1
        lht_coord.points = points
        target.aux_factories[0].update(lh_coord, lht_coord)

        source.remove_coord("level_height")
        target.remove_coord("level_height")

        source.remove_coord("model_level_number")
        target.remove_coord("model_level_number")
        coord = iris.coords.AuxCoord(
            np.arange(4 * 5 * 6).reshape(4, 5, 6), standard_name="model_level_number"
        )
        source.add_aux_coord(coord, [1, 2, 3])
        target.add_aux_coord(coord, [1, 2, 3])
        source.add_dim_coord(lhs_coord, 1)
        target.add_dim_coord(lht_coord, 1)
        msg = "Expecting only a single axis of interpolation, got 3"
        with self.assertRaisesRegex(ValueError, msg):
            source.regrid(target, interpolation.Linear())


@ants.tests.skip_stratify
class TestHybridPressure(ants.tests.TestCase):
    def setUp(self):
        # Ensure that the presence of pressure coordinates does not present a
        # failure when they are equal (i.e. no vertical regrid required).
        self.source = stock.simple_4d_with_hybrid_pressure()
        self.target = self.source.copy()

    def test_equal_pressure_coordinates_present(self):
        # Ensure that the presence of pressure coordinates does not present a
        # failure when they are equal (i.e. no vertical regrid required).
        self.source.regrid(self.target, interpolation.Linear())

    def test_unequal_pressure_coordinates_present(self):
        # Ensure we fall over in the presence of unequal pressure coordinates.
        lh_coord = self.source.coord("level_pressure")
        lh_coord.points = lh_coord.points + 1
        msg = r"Currently pressure coordinates \(air_pressure\) are not " "supported"
        with self.assertRaisesRegex(RuntimeError, msg):
            self.source.regrid(self.target, interpolation.Linear())


if __name__ == "__main__":
    ants.tests.main()
