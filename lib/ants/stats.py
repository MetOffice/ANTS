# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import os
from time import time


class TimeIt(object):
    def __init__(self, t1=None):
        """
        Timing a code snippet.

        Context manager returns the time between entering and exiting the
        context manager.

        Parameters
        ----------
        t1 : :obj:`float`, optional
            Reference start time in seconds since epoch, in UTC.  If not
            provided, this is set to the time of initialisation of this class.

        """
        if t1 is None:
            t1 = time()
        self._t1 = t1

    @property
    def time_taken(self):
        return self._time_taken

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._time_taken = _time_stat(time() - self._t1)


def _time_stat(time):
    time = float(time)
    unit = "s"
    if time > (60 * 60):
        time /= 60 * 60
        unit = "hr"
    elif time > 60:
        time /= 60
        unit = "m"
    return "{}{}".format(time, unit)


def _proc_parse(fnme, fields):
    # More information can be found at https://github.com/torvalds/linux/blob/
    # master/Documentation/filesystems/proc.txt
    def set_suitable_scale(value):
        unit = "kb"
        if value >= 1048576:
            value /= 1048576.0
            unit = "gb"
        elif value >= 1024:
            value /= 1024.0
            unit = "mb"
        return value, unit

    res = {}
    with open(fnme, "r") as fh:
        for line in fh:
            for field in fields:
                if line.startswith(field):
                    val = line.replace(field, "").replace(":", "").strip()
                    val = int(val.lower().strip("kb"))
                    val, unit = set_suitable_scale(val)
                    pval = "{}{}".format(val, unit)
                    res[field] = pval
    return res


def proc_stat():
    """
    Process specific memory statistics

    Return process specific statistics (running process as determined by
    ``os.getpid``) by parsing ``/proc/<pid>/status``

    Returns
    -------
    dict
        Dictionary of process specific statistics 'Memory Statistics PID',
        'VmSize', 'VmRSS', 'VmPeak' and 'VmHWM'.

    """
    # See
    # https://github.com/torvalds/linux/blob/master/Documentation/filesystems/proc.rst
    # for details of what information can be extracted from /proc

    pid = os.getpid()
    fnme = os.path.join("/", "proc", str(pid), "status")
    fields = ["VmSize", "VmRSS", "VmPeak", "VmHWM"]
    res = _proc_parse(fnme, fields)
    res["Process memory Statistics"] = fnme
    return res


def sys_stat():
    """
    System memory statistics

    Return system memory statistics by parsing the host ``/proc/meminfo``.

    Returns
    -------
    dict
        Dictionary containing system memory statistics: 'Committed_AS';
        'MemFree'; 'Buffers'; 'Cached' and 'MemTotal'.

    """
    # See
    # https://github.com/torvalds/linux/blob/master/Documentation/filesystems/proc.rst
    # for details of what information can be extracted from /proc
    fnme = os.path.join("/", "proc", "meminfo")
    fields = ["Committed_AS", "MemFree", "Buffers", "Cached", "MemTotal"]
    res = _proc_parse(fnme, fields)
    res["System memory statistics"] = fnme
    return res
