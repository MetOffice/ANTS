# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""Tests that aren't suited to being testsed with end-to-end functionality in
test__CallbackMetadata.py."""

from ants.io.load import _add_callback, _CallbackMetadata


def test_one_argument_input():
    """Tests that the arguments are correctly returned when given one positional
    argument."""
    callback = _CallbackMetadata(None)
    source = "filepath"
    expected_args = (source,)
    expected_kwargs = {"callback": callback}
    actual_args, actual_kwargs = _add_callback(callback, source)
    assert actual_args == expected_args
    assert actual_kwargs == expected_kwargs


def test_two_argument_input():
    """Tests that the arguments are correctly returned when given two positional
    arguments."""
    callback = _CallbackMetadata(None)
    source = "filepath"
    constraint = "a test constraint"
    expected_args = (source, constraint, callback)
    # this should return an empty dictionary of kwargs
    actual_args, _empty_kwargs = _add_callback(callback, source, constraint)
    assert actual_args == expected_args
    assert _empty_kwargs == {}


def test_three_argument_input():
    """Tests that the arguments are correctly returned when given three positional
    arguments."""
    user_callback = "a callback that will be wrapped in _CallbackMetadata"
    callback = _CallbackMetadata(user_callback)
    source = "filepath"
    constraint = "a test constraint"
    expected_args = (source, constraint, callback)
    # this should return an empty dictionary of kwargs
    actual_args, _empty_kwargs = _add_callback(
        callback, source, constraint, user_callback
    )
    assert actual_args == expected_args
    assert _empty_kwargs == {}


def test_kwargs_input():
    """Tests that arguments are correctly returned when given keyword arguments."""
    callback = _CallbackMetadata(None)
    source = "filepath"
    expected_args = (source,)
    constraint = "a test constraint"
    # user callback will always be removed if passed in as a kwarg before this function
    expected_kwargs = {"constraint": constraint, "callback": callback}
    actual_args, actual_kwargs = _add_callback(callback, source, constraint=constraint)
    assert actual_args == expected_args
    assert actual_kwargs == expected_kwargs
