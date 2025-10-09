# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import ants.tests
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


class TestDiffCS(TestCommon, ants.tests.TestCase):
    # Different coordinate system tests.
    def test_points_inside_projected_crs(self):
        bbox_points = (-12, -12, 7e5, 13e5)
        bbox = self._gen_bbox(*bbox_points)
        res = transform_bbox(bbox, OSGB.crs, UM_SPHERE.crs)
        self.assertEqual(len(res.geoms), 1)
        tar = [-9.49660933, 49.76607039, 3.63474423, 61.46518886]
        self.assertArrayAlmostEqual(res.bounds, tar)

    def test_point_lie_beyond_crs_definition(self):
        bbox = [(-180, -90), (180, -90), (180, 90), (-180, 90)]
        msg = (
            "Attempting to project bounding box (GeogCS(6371229.0)) beyond "
            "the extent of the target coordinate system limits "
            "(TransverseMercator(.*"
        )
        msg = msg.replace("(", r"\(")
        msg = msg.replace(")", r"\)")
        with self.assertRaisesRegex(ValueError, msg):
            transform_bbox(bbox, UM_SPHERE.crs, OSGB.crs)


if __name__ == "__main__":
    ants.tests.main()
