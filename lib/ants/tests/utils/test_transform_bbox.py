# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import re

import ants.tests
import iris.coord_systems
import numpy as np
import pytest
from ants.coord_systems import OSGB, UM_SPHERE
from ants.utils import transform_bbox


class TestCommon(object):
    @staticmethod
    def _gen_bbox(minx, miny, maxx, maxy):
        return [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)]


class TestSameCS(TestCommon, ants.tests.TestCase):
    # Same coordinate system tests.
    #  - No buffer requires when dealing with the same coordinate system.
    def test_points_inside_projected_crs(self):
        bbox_points = (-180, -80, 10, 80)
        bbox = self._gen_bbox(*bbox_points)
        res = transform_bbox(bbox, UM_SPHERE.crs, UM_SPHERE.crs)
        self.assertEqual(len(res.geoms), 1)
        self.assertArrayAlmostEqual(res.bounds, bbox_points)

    def test_points_crossing_dateline_range(self):
        # Test crossing dateline in 0-360 range.
        bbox_points = (170, -80, 200, 80)
        bbox = self._gen_bbox(*bbox_points)
        res = transform_bbox(bbox, UM_SPHERE.crs, UM_SPHERE.crs)
        self.assertEqual(len(res.geoms), 2)
        boxes = sorted([res.geoms[0].bounds, res.geoms[1].bounds], key=lambda x: x[0])
        self.assertArrayAlmostEqual(boxes[0], (-180.0, -80.0, -160.0, 80.0))
        self.assertArrayAlmostEqual(boxes[1], (170.0, -80.0, 180.0, 80.0))

    def test_points_crossing_dateline_range2(self):
        # Here we capture what happens when we pass points which 'should' wrap
        # in the coordinate system provided - this is incorrect as we will
        # return a single geometry in the projected crs (i.e. on a PlateCarree
        # we would connect these via a straight lines).
        bbox_points = (120, -80, -120, 80)
        current_target = (-120, -80, 120, 80)
        bbox = self._gen_bbox(*bbox_points)
        res = transform_bbox(bbox, UM_SPHERE.crs, UM_SPHERE.crs)
        self.assertEqual(len(res.geoms), 1)
        self.assertArrayAlmostEqual(res.bounds, current_target)


@pytest.mark.parametrize(
    "lon_lat_shift",
    [
        [45, 15.0],
        [90.0, 30.0],
        [135.0, 45.0],
        [180.0, 90.0],
    ],
    ids=["(45.0, 15.0)", "(90.0, 30.0)", "(135.0, 45.0)", "(180.0, 90.0)"],
)
def test_um_sphere_remains_invertible(lon_lat_shift):
    """Test that polygons remain invertible for two geodetic crss."""

    lon_shift, lat_shift = lon_lat_shift
    # origin of the UM Sphere in lat, lon
    lat_0, lon_0 = 0, 0

    bbox_points = np.array(
        [lon_0 - lon_shift, lat_0 - lat_shift, lon_0 + lon_shift, lat_0 + lat_shift]
    )

    # Construct a series of bounding boxes
    bbox = [
        (lon_0 - lon_shift, lat_0 - lat_shift),
        (lon_0 + lon_shift, lat_0 - lat_shift),
        (lon_0 + lon_shift, lat_0 + lat_shift),
        (lon_0 - lon_shift, lat_0 + lat_shift),
    ]

    # Project the bounding box from UM Sphere to UM Sphere
    geoms = transform_bbox(bbox, UM_SPHERE.crs, UM_SPHERE.crs)
    bounds = geoms.bounds
    assert np.array_equal(bbox_points, bounds)


class TestDiffCS(TestCommon, ants.tests.TestCase):
    # Different coordinate system tests.
    def setUp(self):
        self.msg = (
            "Attempting to project bounding box (GeogCS(6371229.0)) beyond "
            "the extent of the target coordinate system limits "
            "(TransverseMercator(.*"
        )
        self.msg = self.msg.replace("(", r"\(")
        self.msg = self.msg.replace(")", r"\)")
        super().setUp()

    def test_points_inside_projected_crs(self):
        """Project a bounding box from the OSGB to UM Sphere.

        Notes
        -----
        The ants OSGB crs is a general transverse mercator crs in iris
        which has different projection limits to the cartopy OSGB crs. The
        projection limits for the ants OSGB are the general limits of a transverse
        mercator of (-2e7, -1e7, 2e7, 1e7) and are larger than the cartopy OSGB crs
        which is restricted to a valid domain over the UK (0, 0, 7e5, 13e5).
        """

        # construct a bounding box of points which is nearly the projection limits
        # of the OSGB in cartopy.
        bbox_points = (-12, -12, 7e5, 13e5)
        bbox = self._gen_bbox(*bbox_points)

        # project the bounding box from OSGB to UM Sphere
        res = transform_bbox(bbox, OSGB.crs, UM_SPHERE.crs)
        self.assertEqual(len(res.geoms), 1)

        # The expected domain projected into lat lon.
        tar = [-9.49660933, 49.76607039, 3.63474423, 61.46518886]
        self.assertArrayAlmostEqual(res.bounds, tar)

    def test_ants_osgb_not_invertible_global_poly(self):
        """Test that a polygon spanning the globe is not invertible."""

        inv_msg = re.escape(
            "The bounding box in the crs (TransverseMercator) is not invertible"
            " to the source crs (GeogCS)."
        )

        bbox_points = (-180.0, -90, 180, 90)
        bbox = self._gen_bbox(*bbox_points)
        with self.assertRaisesRegex(ValueError, inv_msg):
            transform_bbox(bbox, UM_SPHERE.crs, OSGB.crs)

    def test_point_lie_beyond_crs_definition(self):
        """Test invalid projection with the iris OSGB.

        As the OSGB crs is a regional crs (transverse Mercator), we only
        get accurate projections within a restricted domain. The iris OSGB
        returns the cartopy OSGB crs when converted to a cartopy projection.
        The projection limits of this domain are (0, 0, 7e5, 13e5). This causes
        any polygons that would exceed this domain to be treated as invalid.

        The bounds are not clipped in this case and instead return NaN.
        """

        # Use the iris OSGB which does use the cartopy OSGB projection limits
        osgb_crs = iris.coord_systems.OSGB()
        bbox_points = (-180, -90, 180, 90)
        bbox = self._gen_bbox(*bbox_points)

        with self.assertRaisesRegex(ValueError, self.msg):
            transform_bbox(bbox, UM_SPHERE.crs, osgb_crs)

    def test_nan_bounds(self):
        """Demonstrate some out-of-domain projections produce NaN bounds
        rather than clipped bounds.

        In this case we define a box which produces bounds of NaN. Once
        we are far from sensible projection limits, invalid polygons can be
        produced.
        """
        # origin of the OSGB in lat, lon
        lat_0, lon_0 = 49.0, -2.0

        # Choose a box that is entirely outside of the valid domain
        bbox_points = (lon_0 + 120, lat_0 - 70, lon_0 + 140, lat_0 - 50)
        bbox = self._gen_bbox(*bbox_points)

        with self.assertRaisesRegex(ValueError, self.msg):
            transform_bbox(bbox, UM_SPHERE.crs, OSGB.crs)


@pytest.mark.parametrize("lon_shift", [85.0, 90.0, 145.0, 180.0])
def test_ants_osgb_not_invertible(lon_shift):
    """Test polygons that are clipped to the domain boundary are not invertible.

    For large enough polygons the bounds of the polygon become
    the bounds of the domain at (-2e7, -1e7, 2e7, 1e7) metres. For domains
    approaching 90 degrees in longitude, the polygons will be clipped.
    """

    # origin of the OSGB in lat, lon
    lat_0, lon_0 = 49.0, -2.0

    inv_msg = re.escape(
        "The bounding box in the crs (TransverseMercator) is not invertible"
        " to the source crs (GeogCS)."
    )

    # construct boxes relative to the domain of interest
    bbox = [
        (lon_0 - lon_shift, lat_0 - 85),
        (lon_0 + lon_shift, lat_0 - 85),
        (lon_0 + lon_shift, lat_0 + 85),
        (lon_0 - lon_shift, lat_0 + 85),
    ]
    with pytest.raises(ValueError, match=inv_msg):
        transform_bbox(bbox, UM_SPHERE.crs, OSGB.crs)
