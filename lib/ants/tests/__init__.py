# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import collections
import functools
import os
import unittest
import warnings

import ants
import numpy as np
import numpy.testing
from ants.config import CONFIG

from . import stock

__all__ = ["stock"]


# Identifies directory for the resource data files needed for unittests.
_RESOURCE_PATH = os.path.join(os.path.split(__file__)[0], "resources")


# Enables skipping tests if there's certain missing dependencies
SKIP_OPTIONAL_TESTS = True


def _skip_importable(module, name):
    skip = unittest.skipIf(
        condition=not module and SKIP_OPTIONAL_TESTS,
        reason="Test requires '{}'.".format(name),
    )
    return skip


def skip_gdal(fn):
    """
    Decorator to choose whether to run tests, based on the availability of the
    libgdal library.

    Example usage:
        @skip_gdal
        class MygdalTest(ants.tests.TestCase):
            ...

    """
    return _skip_importable(ants.fileformats.raster.gdal, "gdal")(fn)


def skip_f90nml(fn):
    """
    Decorator to choose whether to run tests, based on the availability of the
    f90nml library.

    Example usage:
        @skip_f90nml
        class Myf90nmlTest(ants.tests.TestCase):
            ...

    """
    return _skip_importable(ants.fileformats.namelist.f90nml, "f90nml")(fn)


def skip_stratify(fn):
    """
    Decorator to choose whether to run tests, based on the availability of the
    stratify library.

    Example usage:
        @skip_stratify
        class MyStratifyTest(ants.tests.TestCase):
            ...

    """
    return _skip_importable(ants.regrid.interpolation.stratify, "stratify")(fn)


def skip_esmpy(fn):
    """
    Decorator to choose whether to run tests, based on the availability of the
    ESMPy library.

    Example usage:
        @skip_esmpy
        class MyESMPYTests(ants.tests.TestCase):
            ...

    """
    ESMPY_IMPORT_MESSAGE = """To use ESMF, set the ESMFMKFILE environment variable.
https://earthsystemmodeling.org/esmpy_doc/release/latest/html/install.html
#importing-esmpy"""
    if "ESMFMKFILE" not in os.environ:
        warnings.warn(ESMPY_IMPORT_MESSAGE)
        return _skip_importable(ants.regrid.esmf.esmpy, "esmpy")(fn)
    if os.environ.get("ESMFMKFILE") == "":
        warnings.warn(ESMPY_IMPORT_MESSAGE)
        return _skip_importable(ants.regrid.esmf.esmpy, "esmpy")(fn)
    return _skip_importable(ants.regrid.esmf.esmpy, "esmpy")(fn)


def skip_spiral(fn):
    """
    Decorator to choose whether to run tests, based on the availability of the
    compiled 'spiral' search.

    Example usage:
        @skip_spiral
        class MySprialTests(test.IrisTest):
            ...

    """
    return _skip_importable(ants.analysis._merge.spiral, "spiral")(fn)


def get_data_path(relative_path):
    """
    Given the test data resource, returns the full path to the file.

    This should not be needed often in tests - but there are cases where it's
    required.

    """
    if not isinstance(relative_path, str):
        relative_path = os.path.join(*relative_path)
    return os.path.abspath(os.path.join(_RESOURCE_PATH, relative_path))


class TestCase(unittest.TestCase):
    _assertion_counts = collections.defaultdict(int)

    @staticmethod
    def assertArrayEqual(actual, expected, error_message="", verbose=True):
        """
        Test that two numpy arrays are equal.

        Consult the `numpy testing docs
        <https://numpy.org/doc/stable/reference/routines.testing.html#test-support-numpy-testing>`_
        for more details.

        Parameters
        ----------
        actual : np.ma.masked_array
            The first array to compare.
        expected : np.ma.masked_array
            The second array to compare.
        error_message : str, optional
            Message to print on test failure
        verbose : bool, optional
            If True, prints differences between the arrays.

        """
        numpy.testing.assert_array_equal(
            actual, expected, err_msg=error_message, verbose=verbose
        )

    @staticmethod
    def assertArrayAlmostEqual(
        actual, expected, decimal=6, error_message="", verbose=True
    ):
        """
        Test that two numpy arrays are equal.

        Consult the `numpy testing docs
        <https://numpy.org/doc/stable/reference/routines.testing.html#test-support-numpy-testing>`_
        for more details.

        The behaviour of this test may change in a future version of Ants,
        when the numpy version is upgraded.

        Parameters
        ----------
        actual : np.ma.masked_array
            The first array to compare.
        expected : np.ma.masked_array
            The second array to compare.
        decimal : int, optional
            Precision for comparison, defaults to 6.
        error_message : str, optional
            Message to print on test failure
        verbose : bool, optional
            If True, prints differences between the arrays.

        """
        # TODO: should be updated to assert_array_almost_equal_nulp.  Using
        # assert_array_almost_equal for now as a stepping stone.
        # https://code.metoffice.gov.uk/trac/ancil/ticket/1480
        numpy.testing.assert_array_almost_equal(
            actual, expected, decimal=decimal, err_msg=error_message, verbose=verbose
        )

    @classmethod
    def assertMaskedArrayEqual(cls, actual, expected):
        """
        Test that two masked arrays are equal.

        Two checks are performed.  First, the data is checked for equality.
        Secondly, the masks are compared.

        Parameters
        ----------
        actual : np.ma.masked_array
            The first array to compare.
        expected : np.ma.masked_array
            The second array to compare.

        """
        actual = _expand_mask(actual)
        expected = _expand_mask(expected)

        # Check unmasked data:
        cls.assertArrayEqual(actual.data[~actual.mask], expected.data[~expected.mask])
        # Check masks are equal
        cls.assertArrayEqual(actual.mask, expected.mask)

    @classmethod
    def assertMaskedArrayAlmostEqual(cls, actual, expected, decimal=6):
        """
        Test that two masked arrays are equal.

        Two checks are performed.  First, the data is checked for equality.
        Secondly, the masks are compared.

        Parameters
        ----------
        actual : np.ma.masked_array
            The first array to compare.
        expected : np.ma.masked_array
            The second array to compare.
        decimal : int
            Precision for comparison, defaults to 6.

        """
        # Default precision of 6 to match numpy/iris

        actual = _expand_mask(actual)
        expected = _expand_mask(expected)

        # Check unmasked data is equal
        cls.assertArrayAlmostEqual(
            actual.data[~actual.mask],
            expected.data[~expected.mask],
            decimal=decimal,
        )
        # Check masks are equal
        cls.assertArrayEqual(actual.mask, expected.mask)

    @classmethod
    def setUpClass(cls):
        # Ensure that tests are not sensitive to user configuration except
        # for the testing section.
        CONFIG.__init__()
        os.environ["ANTS_NPROCESSES"] = str(1)
        CONFIG.config["ants_decomposition"]["x_split"] = 3
        CONFIG.config["ants_decomposition"]["y_split"] = 3


def _expand_mask(array):
    """
    Return array as masked array with a mask value for each data point.

    Converts a masked array with a mask of a single boolean False to an array
    of False values, or converts a numpy array to a masked array.

    Parameters
    ----------
    array : :class:`np.ma.masked_array`
    Array that may have a single boolean for a mask.

    Returns
    -------
    : :class:`np.ma.masked_array`
    Masked array with a masked value for every data point.

    """
    return np.ma.masked_array(array, mask=(np.zeros(array.shape, dtype=bool)))


def enable_all_lazy_data(test_function):
    """Configure test_function to load data lazily, regardless of the size of the data.

    From iris 3.5, small datasets are realised on load.  For testing, it's
    sometimes necessary to have small datasets load lazily.

    This function should only be used for testing.

    Parameters
    ----------
    test_function : :class:`collections.abc.Callable`
    Function (or other callable) which should always load data lazily.

    Returns
    -------
    :class:`collections.abc.Callable`
    Function (or other callable) which loads data lazily.
    """

    @functools.wraps(test_function)
    def wrapper(*args, **kwargs):
        if (
            hasattr(
                ants.utils.cube.iris.fileformats.netcdf.loader,
                "_LAZYVAR_MIN_BYTES",
            )
            is False
        ):
            raise RuntimeError(
                "Expected "
                "_LAZYVAR_MIN_BYTES in iris.fileformats.netcdf.loader attributes"
                "(introduced in iris3.5) to control realising small datasets.  "
                "This variable was not found, suggesting a change in iris.  "
                "These tests need to be updated accordingly."
            )
        if ants.utils.cube.iris.fileformats.netcdf.loader._LAZYVAR_MIN_BYTES != 5000:
            raise RuntimeError(
                "iris.fileformats.netcdf.loader._LAZYVAR_MIN_BYTES no longer has the "
                "default value of 5000 introduced at iris 3.5.  These tests need to "
                "be updated accordingly."
            )
        ants.utils.cube.iris.fileformats.netcdf.loader._LAZYVAR_MIN_BYTES = 0
        result = test_function(*args, **kwargs)
        ants.utils.cube.iris.fileformats.netcdf.loader._LAZYVAR_MIN_BYTES = 5000
        return result

    return wrapper
