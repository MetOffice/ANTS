# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

"""
This module provides functions related to time handling for ancillary files.

"""
import itertools

import ants
import cf_units
import numpy as np

_FLH_TIME_INDICATOR = {"periodic": 2, "time_series": 1, "single": 0}


def _flh_date(date1, unit):
    # A function required to extract dates.  Netcdf datetime objects do not
    # have operators allowing deltatimes like in the standard datetime
    # library, and date can be either a datetime.datetime or a
    # netcdftime.datetime.
    date = unit.num2date(date1)
    return np.array(
        [date.year, date.month, date.day, date.hour, date.minute, date.second]
    )


def _flh_time_indicator(time_coordinate):
    # Infer what type of time series is present if present at all.
    # Attempt to infer the F03 ancil time indicator from the cube
    # This is not straight forward in the periodic case,
    # We are not sure we have it right, we expect to review as
    # we see more cases.
    if is_periodic(time_coordinate):
        result = _FLH_TIME_INDICATOR["periodic"]
    elif time_coordinate.points.size != 1:
        result = _FLH_TIME_INDICATOR["time_series"]
    else:
        result = _FLH_TIME_INDICATOR["single"]
    return result


def _get_other_intervals(interval, start_times, end_times):
    """
    Return differences between start_times and end_times not equal to interval.

    Algorithm is that the difference is computed between each start_time and
    the corresponding end_time, and this difference is compared to interval.
    If the difference is equal to the interval, it's discarded, so the final
    result is any differences that are not equal to the interval.

    This means that an empty list is returned if, for all indices N:
    start_times[N] - end_times[N] == interval

    Interval, and each element of start_times and end_times are numpy arrays,
    using the same array format of a six element array, where first element is
    years, second is months, third is days, fourth is hour, fifth is minutes
    and the final element is seconds.

    Parameters
    ----------
    interval: :class:`np.ndarray`
        Interval to remove from returned result.
    start_times: :class:`np.ndarray`
        Sequence of arrays where each array contains a time stamp, i.e. LBYR,
        LBMON etc from F03.
    end_times: :class:`np.ndarray`
        Sequence of arrays where each array contains a time stamp, i.e. LBYRD,
        LBMOND etc from F03.

    Returns
    -------
    : list of :class:`np.ndarray`
        Differences between each start and end time that is not equal to interval.

    Examples
    --------

    Consistent difference of one month between start and end times:

    >>> interval = np.array([0, 1, 0, 0, 0, 0])
    >>> start_times = [np.array([0, i, 0, 0, 0, 0]) for i in range(4)]
    >>> end_times = [np.array([0, i, 0, 0, 0, 0]) for i in range(1, 5)]
    >>> _get_other_intervals(interval, start_times, end_times)
    []

    And now let's make the final end time have a difference of one month and
    one second from the final start time:

    >>> end_times[-1] = np.array([0, 4, 0, 0, 0, 1])
    >>> _get_other_intervals(interval, start_times, end_times)
    [array([0, 0, 0, 0, 0, 1])]

    """
    # Returns any time intervals between each point in start_times and the
    # corresponding point in end_times that are not equal to interval
    result = [
        x
        for x in map(lambda x, y: (y - x - interval), start_times, end_times)
        if x.any()
    ]
    rollover_monthly_result = np.array([1, -12, 0, 0, 0, 0])

    count = 0
    for item in result:
        if np.array_equal(item, rollover_monthly_result):
            count += 1

    # If all arrays held in the list are the same as rollover_monthly_result
    # then return an empty list
    if count == len(result):
        result = []

    return result


def _get_flh_interval_as_array(time_coord):
    """
    Return the interval for the time coordinate defined for this instance.

    An interval is returned when any of the following conditions are met:

    1. The time coordinate is bounded.
    2. The bounds are contiguous i.e. the upper bound for point N must be
       coincident with the lower bound for point N+1.
    3. The difference between the two bounds for each time is exactly 1
       year, exactly 1 month or a positive integer number of days.

    An exception is thrown when none of the above conditions are met.

    If the time coordinate should have an interval detectable by the above
    definition, but is not recognised as such by this function, a
    preprocessing stage may be required to change the time information to
    conform to the above criteria.

    Returns
    -------
    : :class:`numpy.ndarray`
        Returned interval is in the form of a numpy array suitable for
        insertion into the the raw fixed length header.  0th element of array
        corresponds to entry 35 in the FLH, 1st element is entry 36 and so
        on through to 5th element of the array being entry 40 in FLH.

    """

    def _get_monthly_or_annual_interval(time_coord):
        """
        Identifies whether there's a monthly, annual or neither interval.

        Returns None for neither monthly nor annual interval between lower
        bound and upper bound for each point in the time_coord;
        otherwise returns array specifying either month or annual interval
        in suitable format for FLH.

        """
        intervals = {
            "annual": np.array([1, 0, 0, 0, 0, 0]),
            "monthly": np.array([0, 1, 0, 0, 0, 0]),
        }
        interval = None
        units = time_coord.units
        if time_coord.has_bounds():
            lower_bounds = [_flh_date(t[0], units) for t in time_coord.bounds]
            upper_bounds = [_flh_date(t[1], units) for t in time_coord.bounds]
        else:
            lower_bounds = [_flh_date(t, units) for t in time_coord.points[0:-1]]
            upper_bounds = [_flh_date(t, units) for t in time_coord.points[1:]]

        for key in intervals.keys():
            other_intervals = _get_other_intervals(
                intervals[key], lower_bounds, upper_bounds
            )
            if len(other_intervals) == 0:
                interval = intervals[key]
        return interval

    def _get_regular_interval(time_coord, duration):
        """
        Identifies whether there's a regular interval on the coordinte.

        Note that a regular interval is not dependent on the calendar -
        i.e. it is daily or more frequent.

        duration can be either 'days' or 'hours'.

        Returns None if there is no regular interval that is an integer
        multiple of the duration between start_times and end_times; otherwise
        returns array in suitable format for FLH.

        """
        # Hard-coded unit origin since we rely on a unit of 'duration since',
        # but can't readily extract that from cf_units since the strfmt can
        # fall over with years prior to 1900.  For the purpose of this
        # function, the actual origin year is irrelevant: it's the differences
        # between dates, not the absolute values of those dates, that matters.

        units = "{} since epoch".format(duration)
        time_units_since = cf_units.Unit(units, calendar=time_coord.units.calendar)

        if time_coord.has_bounds():
            bounds = time_coord.units.convert(time_coord.bounds, time_units_since)
            interval = np.unique(np.diff(bounds, axis=1))
        else:
            points = time_coord.units.convert(time_coord.points, time_units_since)
            interval = np.unique(np.diff(points))

        if len((interval)) != 1:
            return None
        # Trap for fractions of a day interval - i.e. hourly, minutely,
        # secondly interval
        if interval[0] != int(interval[0]):
            return None
        base = _flh_date(0, time_units_since)
        interval = _flh_date(interval[0], time_units_since) - base
        return interval

    if time_coord.has_bounds() and not time_coord.is_contiguous():
        msg = "F03 ancillaries with time bounds are required to be contiguous."
        raise ValueError(msg)
    if not time_coord.has_bounds():
        try:
            time_coord = time_coord.copy()
            ants.utils.coord.guess_bounds(time_coord)
        except ValueError:
            pass

    interval = _get_monthly_or_annual_interval(time_coord)
    if interval is None:
        interval = _get_regular_interval(time_coord, "days")
    if interval is None:
        interval = _get_regular_interval(time_coord, "hours")
    if interval is None:
        raise RuntimeError(
            "Time interval not supported: F03 requires "
            "intervals between successive times to be "
            "consistent (contiguous). In addition, Ants "
            "support is currently limited to intervals of "
            "either 1 year, 1 month or an integer number of "
            "days."
        )
    return interval


def set_headers_time_information(cube, headers):
    """
    Modifies the provided headers with time information derived from the cube.

    Parameters
    ----------
    cube : :class:`iris.cube.Cube`
        The cube used to derive the time information to insert into the
        headers.
    headers : dict
        Dictionary of values describing the headers of an ancillary file
        to which time information needs to be added.  The headers
        dictionary is edited in place.

    """
    flh = headers["fixed_length_header"]

    time_coords = ants.utils.cube.find_time_coordinates(cube)
    if len(time_coords) == 1:
        times = time_coords[0]

        flh["time_type"] = _flh_time_indicator(times)
        tunit = times.units
        headers["integer_constants"]["num_times"] = times.points.size

        if times.points.size != 1:
            # Initial data time
            initial_time = _flh_date(times.points[0], tunit)
            flh["t1_year"] = initial_time[0]
            flh["t1_month"] = initial_time[1]
            flh["t1_day"] = initial_time[2]
            flh["t1_hour"] = initial_time[3]
            flh["t1_minute"] = initial_time[4]
            flh["t1_second"] = initial_time[5]

            # Validity data time
            validity_time = _flh_date(times.points[-1], tunit)
            flh["t2_year"] = validity_time[0]
            flh["t2_month"] = validity_time[1]
            flh["t2_day"] = validity_time[2]
            flh["t2_hour"] = validity_time[3]
            flh["t2_minute"] = validity_time[4]
            flh["t2_second"] = validity_time[5]

            # Time interval
            interval = _get_flh_interval_as_array(times)
            flh["t3_year"] = interval[0]
            flh["t3_month"] = interval[1]
            flh["t3_day"] = interval[2]
            flh["t3_hour"] = interval[3]
            flh["t3_minute"] = interval[4]
            flh["t3_second"] = interval[5]

            # Set calendar if required (otherwise, defaults to IMDI)
            is_not_monthly = np.any(interval[:2] == 0)
            is_daily = np.any(interval[2:] != 0)
            is_short_interval = is_not_monthly and is_daily

            if is_short_interval:
                # cf-units 2 (iris 2.1+) uses calendar aliases so we won't
                # necessarily have to support the different names.
                calendars = {
                    "standard": 1,
                    "proleptic_gregorian": 1,
                    "gregorian": 1,
                    "360_day": 2,
                    "365_day": 3,
                    "noleap": 3,
                }
                try:
                    calendar = calendars[tunit.calendar]
                except KeyError:
                    raise ValueError(
                        "{} is not a suitable calendar for fields files".format(
                            tunit.calendar
                        )
                    )
                flh["calendar"] = calendar
    else:
        flh["time_type"] = _FLH_TIME_INDICATOR["single"]
        coord_cat_time = ["month", "day", "year", "season"]
        coord_names = [coord.name() for coord in cube.coords()]
        pairs = itertools.product(coord_cat_time, coord_names)
        for cat_time, coord_name in pairs:
            if cat_time in coord_name:
                msg = (
                    'Categorisation time coordinates found "{}".  '
                    "Underspecified time information, please consider "
                    'adding a "time" coordinate if applicable.'
                )
                raise ValueError(msg.format(coord_name))


def is_periodic(times):
    """
    Tests whether a time coordinate corresponds to a periodic ancillary.

    It is not easy to determine whether a time coordinate should be treated
    as periodic or not.  This implementation only looks for annual
    periodicity.  If you have times with different periodicity then this
    function will need adapting.

    A time coordinate is annual and periodic if the end bound
    of the last time is exactly one year after the start bound of the first
    time.  If this does not work for your time coordinate first ensure that
    your time coordinate is consistent with CF use of bounds.
    You may need to  pre-process the bounds values as necessary.

    If your time coordinate is annually periodic, is not recognised as
    periodic by this function and editing would change the meaning of the
    data then this function may need adapting.

    Parameters
    ----------
    times :  :class:`iris.coords.Coord`
        Time coordinate to examine.
    Returns
    -------
    : bool
        Whether times are identified as periodic or time series.  True
        means the time coordinate is periodic.

    Raises
    ------
    ValueError
        If the provided times coordinate is not recognised as a time.

    """
    result = False
    units = times.units
    if units.is_time() is False and units.is_time_reference() is False:
        msg = "Can only test time coordinates for periodicity.  {} is not time".format(
            times.name()
        )
        raise ValueError(msg)
    if times and times.has_bounds() and len(times.points) > 1:
        # Why tuple the timetuple result?  datetime.datetime.timetuple returns
        # a struct_time rather than a tuple.
        start_time = tuple(units.num2date(times.bounds[0][0]).timetuple())
        end_time = tuple(units.num2date(times.bounds[-1][-1]).timetuple())

        result = True
        if end_time[0] != start_time[0] + 1:
            result = False
        if end_time[1:6] != start_time[1:6]:
            # Why limit to 1:6?  Entries 6, 7 and 8 in time tuple are day of
            # week, day of year and dst flag - we don't care about those, and
            # day of week in particular changes from one year to the next.
            result = False

    return result
