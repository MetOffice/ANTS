# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
A collection of frequently required preprocessing steps for mule.UMFile
objects.

Available functionality includes:

#. Update time origin to avoid issues with dates defined in year 0
   (update_reference_year).
#. Make the existing bounds on a time coordinate contiguous
   (make_time_bounds_contiguous).
#. Explicitly set and override climatology year (set_climatology_year).
#. Fix lbproc value where possible (correct_lbproc).
#. Create a metadata.ini file for climatology time information (write_metadata_file)

"""
import configparser
import numbers
from collections import Counter

import cftime
import numpy as np


def update_reference_year(ffv, year=None):
    """
    Update origin year of the time coordinate.

    Either sets the year to the provided year, or defaults to setting it to
    4AD.  If the file to be fixed does not correspond to a leap year,
    please provide a year to over-ride the 4AD default.

    Parameters
    ----------
    ffv : :class:`mule.UMFile` object.
        The input UM file which we want to update.
    year : :obj:`int`, optional
        The year to switch the origin of the time coordinate to.  The provided
        year must be greater than 0.

    Warnings
    --------
    + If no year is provided, it is assumed that the data should be shifted to
      a leap year.  To avoid this, provide a year parameter that is not a leap
      year.

    """
    if year is None:
        year = 4
    elif year <= 0 or not isinstance(year, numbers.Integral):
        raise ValueError("The provided year must be a positive integer.")
    offset = year - ffv.fixed_length_header.t1_year
    ffv.fixed_length_header.t1_year = year
    ffv.fixed_length_header.t2_year = offset + ffv.fixed_length_header.t2_year
    for field in ffv.fields:
        field.lbyr += offset
        field.lbyrd += offset


def make_time_bounds_contiguous(ffv, final_bound=None):
    """
    Make exising time bounds contiguous.

    The definition of contiguous used is that the start time of one cell is
    exactly the same as the end time of the preceding cell chronologically.

    In addition, the final cells (in terms of time - i.e. all the cells with
    the same time value as the final cell) are adjusted such that they end
    exactly one year after start of the first cells.  This means that the data
    spans exactly one year.

    If the data should not span exactly a year, or if the automatic upper bound
    detection fails on the final cells, call this function with a tuple
    provided to the final_bound keyword argument, where the first element is
    the desired lbyrd, second element is the desired lbmond and so on, through
    to the final element being lbsecd.

    Parameters
    ----------
    ffv : :class:`mule.UMFile` object.
        The input UM file which we want to update.
    final_bound : :obj:`tuple`, optional
        A six element tuple, where the first element is the desired lbyrd,
        second element is the desired lbmond and so on, through to the final
        element being lbsecd.

    Warnings
    --------
    + No checking is done to ensure that the data is appropriate to be made
      contiguous or that the provided final_bound is consistent with the data.

    + If the final_bound parameter is not supplied, the file is assumed to be
      intended to cover exactly one year.  If this is not the case, the end
      time of the final cells will be wrong: there is no attempt to compute
      the end time of the final cell based on the times in the preceding
      cells.

    """

    def _is_same_number_of_fields(fields):
        counter = Counter()
        for field in fields:
            time = ",".join([str(time) for time in field.raw[1:13]])
            counter[time] += 1
        if len(np.unique((list(counter.values())))) != 1:
            return False
        return True

    def _find_fields_per_time(fields):
        # How many fields do we have for each time? (i.e. same time, different
        # stash or pseudo level)
        first_field = fields[0]
        start_time_bounds = first_field.raw[1:13]
        fields_per_time = 1
        for field in fields[1:]:
            if np.array_equal(field.raw[1:13], start_time_bounds):
                fields_per_time += 1
            else:
                break
        return fields_per_time

    if len(ffv.fields) < 2:
        msg = (
            "Need at least 2 fields in the file to make contiguous bounds."
            "  Found {}.".format(len(ffv.fields))
        )
        raise ValueError(msg)

    if _is_same_number_of_fields(ffv.fields) is False:
        msg = "Need same number of fields for each time"
        raise ValueError(msg)

    fields_per_time = _find_fields_per_time(ffv.fields)

    # For each batch of fields with the same time, set the upper bound to the
    # lower bound of the field directly after them (protects, in particular,
    # against common weirdness around February bounds).
    batches = len(ffv.fields) // fields_per_time - 1
    for batch in range(batches):
        start = batch * fields_per_time
        upper_bound = ffv.fields[start + fields_per_time + 1].raw[1:7]
        for field in ffv.fields[start : (start + fields_per_time + 1)]:
            field.raw[7:13] = upper_bound

    # And for the last batch of fields in terms of time, since there's no
    # fields after it, we infer the upper bound from adding one year to the
    # first field...
    if final_bound is None:
        for field in ffv.fields[-fields_per_time:]:
            field.raw[7] = ffv.fields[0].raw[7] + 1
            field.raw[8:13] = ffv.fields[0].raw[2:7]
    else:
        # ...unless the user has given us an explicit bound to use instead.
        if len(final_bound) != 6:
            raise ValueError("Final bound needs to be a 6 element sequence")
        for field in ffv.fields[-fields_per_time:]:
            field.raw[7:13] = final_bound


def set_climatology_year(ffv, year):
    """
    Set the climatology year.

    Set the climatology year, overriding all fixed length header time
    information and field time information in the process.  This is most
    useful for those files where a year of 0 has been used to denote a periodic
    climatology.  The calendar is determined from the time bounds specified
    in the fields.  The only assumption is that field.lbmon values are correct
    as this determines ordering.

    Parameters
    ----------
    ffv : :class:`mule.UMFile` object.
        The input UM file which we wish to fill the climatology year
        information.
    year : int
        Year of the climatology.

    Returns
    -------
    : None
        In-place operation

    Warnings
    --------
    To be used at the users discretion.

    """

    year = int(year)

    # Derive the calendar from the time information present.
    maximum_day = np.array([[field.lbdat, field.lbdatd] for field in ffv.fields]).max()
    calendar = 2
    if maximum_day > 30:
        calendar = 1

    ffv.fixed_length_header.time_type = 2
    ffv.fixed_length_header.t1_year = year
    ffv.fixed_length_header.t1_month = 1
    ffv.fixed_length_header.t1_day = 1
    ffv.fixed_length_header.t1_hour = 1
    ffv.fixed_length_header.t1_minute = 0
    ffv.fixed_length_header.t2_year = year
    ffv.fixed_length_header.t2_month = 12
    ffv.fixed_length_header.t2_day = 1
    ffv.fixed_length_header.t2_hour = 1
    ffv.fixed_length_header.t2_minute = 0
    ffv.fixed_length_header.t3_year = 0
    ffv.fixed_length_header.t3_month = 1
    ffv.fixed_length_header.t3_day = 0
    ffv.fixed_length_header.t3_hour = 0
    ffv.fixed_length_header.t3_minute = 0

    for field in ffv.fields:
        field.lbmin = field.lbmind = 0
        field.lbhr = field.lbhrd = 0
        field.lbdat = field.lbdatd = 1
        field.lbtim = 20 + calendar  # time-mean (20)
        field.lbyr = field.lbyrd = year
        field.lbsec = field.lbsecd = 0
        field.lbmind = field.lbmind = 0
        if field.lbmon + 1 > 12:
            field.lbmond = 1
            field.lbyrd = year + 1
        else:
            field.lbmond = field.lbmon + 1


def correct_lbproc(ffv):
    """
    Set lbproc value to 0 where it is found to be negative.

    Commonly, field.lbproc values are incorrectly set to the integer missing
    data indicator value (-32768), intending to denote that no processing has
    been done.  However this is incorrect, and so this function overrides this
    with the value 0 as per F03.

    Parameters
    ----------
    ffv : :class:`mule.UMFile` object.

    Returns
    -------
    : None
        In-place operation

    Warnings
    --------
    To be used at the users discretion.

    """
    for field in ffv.fields:
        if field.lbproc < 0:
            field.lbproc = 0


def _create_climatology_config(ffv):
    """
    Creates a configparser object containing the time metadata to write out in a .ini
    file. Only suitable to use with monthly mean multi year climatologies.

    """
    if ffv.fixed_length_header.t3_month != 1:
        raise ValueError(
            "Ancil file does not appear to be a monthly mean multi year climatology. "
            "(fixed_length_header.t3_month != 1)"
        )

    # Find first and last field
    first_field = ffv.fields[0]
    last_field = ffv.fields[-1]
    # Create datetime objects for the start date and end date of the climatology
    start_date = cftime.datetime(first_field.lbyr, first_field.lbmon, first_field.lbdat)
    end_date = cftime.datetime(last_field.lbyrd, last_field.lbmond, last_field.lbdatd)
    # Create configparser object that contains the information to be written to the
    # .ini file
    config = configparser.ConfigParser()
    config["climatology"] = {}
    config["climatology"][
        "cell_methods"
    ] = "time: mean within years time: mean over years"
    config["climatology"]["bounds_diff"] = "month"
    config["climatology"]["start"] = start_date.strftime("%Y-%m-%d")
    config["climatology"]["end"] = end_date.strftime("%Y-%m-%d")
    return config


def write_metadata_file(ffv, output_filepath):
    """
    Write a metadata.ini file for time metadata.

    Write a metadata.ini file for time metadata in cases where the time information in
    the fixed length header and field has been changed (typically for climatologies,
    by set_climatology year()). Therefore, if this is to be used alongside
    set_climatology_year(), it should be called first. It is only suitable for use with
    monthly mean multi year climatologies. The format of the output file will be, for
    example:
    [climatology]
    cell_methods: time: mean within years time: mean over years
    bounds_diff: month
    start: 1998-01-01
    end: 2008-01-01

    Parameters
    ----------
    ffv : :class:`mule.UMFile` object.
        The input UM file which we wish to fill the climatology year
        information.
    output_filepath : str
        The location for the output metadata.ini file.

    Returns
    -------
    : None
        In-place operation

    Warnings
    --------
    To be used at the users discretion.

    """

    config = _create_climatology_config(ffv)

    with open(output_filepath + "_metadata.ini", "w") as configfile:
        config.write(configfile)
