# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
# Parsing the rose app configuration files using Python's built-in config
# parser.
"""
This module handles the run-time configuration of the ANTS library.

Certain hooks are present in the library for providing detailed control over
ANTS run-time.

The configuration of ANTS follows a first-in first-out approach on parsing
configuration options and is handled by
:class:`ants.config.GlobalConfiguration`.  This means that any number of
configuration files can be parsed.  On import, `ants.cfg` is parsed when
present in the lib/ants/ folder.  Each successive configuration file parsing
will override existing parameter values.

Additionally, the following environmental variable hooks are available:

* ANTS_NPROCESSES: Number of processes to be used by ants decomposition.

  * Takes an integer value corresponding to the number of processes desired.
    Additionally take the value 'max', which corresponds to utilising all
    available CPUs on the running hardware (defaults to 1).

  * Redundant where a scheduler is used (SLURM, PBS, LSF).  The relevant
    scheduler environment variable "SLURM_NTASKS", "PBS_NP" or
    "LSB_DJOB_NUMPROC" is used instead.

* ANTS_TEMPORARY_DIR: A user configured space used for temporary files.
  When decomposition is enabled large volumes of temporary data
  may be created, so it is useful to choose a location that can
  handle this (e.g. a personal SCRATCH space). ANTS cache and temporary
  file usage will utilise this location.

  If this variable is set, it must
  be to a directory that already exists.

  If this variable is not set, the
  default temporary directory is used. For further information about how
  this directory is chosen, please see:
  https://docs.python.org/3/library/tempfile.html#tempfile.gettempdir

* CARTOPY_DATA_DIR: Directory for Natural Earth data required by cartopy.
  To ensure reproducibility, this should be set to a curated location.  Default
  is to use the cartopy default cache location (which means different users may
  see different results). This environment variable is read by cartopy directly.

"""
import argparse
import configparser
import copy
import io
import itertools
import logging
import os
import re
import tempfile

from ants.exceptions import TimeConstraintFormatException

_DEFAULT_CONFIG_PATHS = [os.path.join(os.path.dirname(__file__), "ants.cfg")]
_LOGGER = logging.getLogger(__name__)

TOLERANCE = 1e-10


def _expand_path(path):
    return os.path.realpath(os.path.expandvars(os.path.expanduser(path)))


def set_temporary_directory():
    # Set the temporary directory to one given by the user in the environment variable
    tempfile.tempdir = os.getenv("ANTS_TEMPORARY_DIR")
    if tempfile.tempdir:
        _LOGGER.info(f"ANTS_TEMPORARY_DIR is set to: {tempfile.tempdir}")


def filepath_readable(filepath):
    """
    Check read permissions of the provided filepath.

    Parameters
    ----------
    filepath : str
        Filepath to check read permissions.
        The path is expanded in the case of environmental variables and '~'.
        Symbolic links are also supported in the path.

    Raises
    ------
    argparse.ArgumentTypeError
        If the filepath does not have read permissions or does not exist.

    Returns
    -------
    filepath : str
        Canonical expanded filepath.

    """

    filepath = _expand_path(filepath)
    if not os.path.exists(filepath):
        raise argparse.ArgumentTypeError("{} does not exist.".format(filepath))
    if not os.access(filepath, os.R_OK):
        msg = "You do not have read permissions to {}"
        msg = msg.format(filepath)
        raise argparse.ArgumentTypeError(msg)
    return filepath


def dirpath_writeable(filepath):
    """
    Check read-write permissions of the provided path.

    Parameters
    ----------
    filepath : str
        File path to check read-write permissions.
        The path is expanded in the case of environmental variables and '~'.
        Symbolic links are also supported in the path.
        The directory the file is contained in is checked for read-write
        permissions.

    Raises
    ------
    IOError
        If the directory path does not have read-write permissions.

    Returns
    -------
    filepath: str
        Canonical expanded file path.

    """
    # Note: utils is dependent on ants.config.CONFIG and so this function
    # cannot move to utils without a circular dependency.
    filepath = _expand_path(filepath)
    dirpath = os.path.dirname(filepath)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    if not os.access(dirpath, os.R_OK & os.W_OK):
        msg = "You do not have read-write permissions to {}"
        msg = msg.format(dirpath)
        raise IOError(msg)
    return filepath


def formatted_time(time_string):
    """
    Converts provided string into a datetime object as required by iris.

    Parameters
    ----------
    time_string : str
        A string containing information about the time constraints for the
        data to enable it to be split into year long chunks.

    Raises
    ------
    TimeConstraintFormatException
        If the string is not of the required (YYYY) format.

    Returns
    -------
    datetime: int
        datetime as required by iris.

    """
    if time_string is None:
        pass
    else:
        pattern = re.compile(r"\A\d{4}\Z")
        if re.match(pattern, time_string):
            return int(time_string)
        else:
            raise TimeConstraintFormatException(time_string=time_string)


def _initialise_logger(level=None):
    """
    Convenience function for users initialising the logger when running their
    applications.

    """
    if level is None:
        level = logging.INFO

    logger = logging.getLogger()
    logger.setLevel(level)
    fmt = (
        "LOGGER: %(name)s;%(levelname)s;%(asctime)s;%(filename)s;"
        "L%(lineno)s;%(message)s"
    )
    # Date in ISO 8601 format
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S")

    # Stream log to the console
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class _Singleton(type):
    # https://stackoverflow.com/q/6760685
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class GlobalConfiguration(object, metaclass=_Singleton):
    """
    The global configuration class handles any number of configuration files,
    where subsequent configuration entries act to override previous entries
    parsed.

    All group names are prefixed with "ants" and all entries are then parsed
    strictly.  Those groups not prefixed with "ants" are silently ignored.

    The following represents a description of the runtime configuration
    options and their default values::

        # Decomposition framework

        [ants_decomposition]
        # Decomposition breaks a computation down into smaller pieces.

        # The total numbers of pieces is the product of the `x_split` and
        # `y_split` parameters below.  Increasing the number of pieces results
        # in more, but smaller, pieces so reduces total memory usage at the
        # cost of needing more CPUs, more time or both.  The total number of
        # pieces may be more than the available CPUs - remaining pieces will
        # be queued and run when CPUs are available.

        # The allowed combinations of x_split and y_split are as follows:
        # * Both splits set to numbers greater than or equal to 1:
        # decomposition occurs as described above. The two splits do not need
        # to be the same number, but they must both be specified.
        # * Both splits set to automatic: Ants will decompose to 800Mb chunks.
        # * Both splits set to 0: decomposition will be disabled.
        # * Neither split specified: decomposition will be disabled.

        # Number of pieces to decompose over x. It is recommended that a
        # user configure this. See above for the allowed combinations of
        # x_split and y_split.
        x_split

        # Number of pieces to decompose over y. It is recommended that a
        # user configure this. See above for the allowed combinations of
        # x_split and y_split.
        y_split

        # Pad width to use when extracting source pieces which overlap with
        # target pieces. Default is 1.
        pad_width

        # Regridding
        [ants_regridding_horizontal]
        # Specify the regridding scheme wanted (see ants.regrid).
        # Either a value for ants_regridding_horizontal or
        # a value for ants_regridding_vertical *must be provided*.
        # It is also possible to specify both if required.
        # Available horizontal regridding options are:
        #  * Linear,
        #  * TwoStage,
        #  * ConservativeESMF,
        #  * AreaWeighted,
        #  * Nearest
        # Default is None.
        scheme

        # Specify the extrapolation mode to be used for horizontal regridding.
        # Note that not all schemes support extrapolation, e.g. AreaWeighted.
        # In these cases, providing an extrapolation mode will result in an error.
        # Permitted extrapolation modes will depend on the scheme, refer to the
        # documentation for the selected scheme to find the extrapolation modes
        # it supports.
        # Default is None, i.e. use the selected scheme's default extrapolation mode.
        extrapolation_mode

        [ants_regridding_vertical]
        # Specify the regridding scheme wanted (see ants.regrid).
        # Either a value for ants_regridding_horizontal or
        # a value for ants_regridding_vertical *must be provided*.
        # It is also possible to specify both if required.
        # Available vertical regridding options are:
        #  * Linear,
        #  * Conservative,
        #  * Nearest
        # Default is None.
        scheme

        # Specify the extrapolation mode to be used for vertical regridding.
        # Note that not all schemes support extrapolation, e.g. Conservative.
        # In these cases, providing an extrapolation mode will result in an error.
        # Permitted extrapolation modes will depend on the scheme, refer to the
        # documentation for the selected scheme to find the extrapolation modes
        # it supports.
        # Default is None, i.e. use the selected scheme's default extrapolation mode.
        extrapolation_mode

        # Additional metadata in the context of writing output (for those
        # formats that support it - currently only NetCDF).
        [ants_metadata]
        history

        [ants_tolerance]
        # Specify the tolerance wanted for the checks conducted by the Raymond
        # filter on a grid if isotropic filtering is requested. The default
        # ANTS tolerance is used if this is not set.
        raymond_filter_isotropy_tolerance

        [ants_tuning]
        # The behaviour of dask rechunking on save gives better performance in
        # most cases.  However, if the source data is a netCDF with contiguous
        # netCDF chunking, then it may be more performant to disable the dask
        # rechunking by setting this option to True (which was the default
        # behaviour up to and including ANTS 0.19).
        disable_rechunking

    Additionally there are some configurations which may be useful to
    debugging and or developers::

        # Logging setup
        [ants_logging]
        # Simply set to True to enable application logging.
        enabled

        # Defaults to INFO.  See
        # https://docs.python.org/3/library/logging.html#logging-levels for
        # more options.
        level

    """

    # Variables defaults should not be defined.  We need to distinguish between
    # specified vs unspecified by the user.
    # Logic around default values belong in the functions which use them.

    # Global variables
    _GLOB_PARAMETERS = {"saver": None}
    # These are the parameters that are interpreted from the INI files (via
    # configparser).
    _INI_PARAMETERS = {
        "ants_logging": {"enabled": None, "level": None},
        "ants_decomposition": {"x_split": None, "y_split": None, "pad_width": None},
        "ants_metadata": {"history": None},
        "ants_regridding_horizontal": {"scheme": None, "extrapolation_mode": None},
        "ants_regridding_vertical": {"scheme": None, "extrapolation_mode": None},
        "ants_tolerance": {"raymond_filter_isotropy_tolerance": None},
        "ants_tuning": {"disable_rechunking": None},
        "ants_fill": {"kdtree_latitude_scale": None},
    }

    def __init__(self):
        self.config = copy.deepcopy(self._INI_PARAMETERS)
        self.config.update(self._GLOB_PARAMETERS)
        self._config = configparser.RawConfigParser()

    def __str__(self):
        return str(self.config)

    def __repr__(self):
        fmt = "{cls}({self.config!r})"
        result = fmt.format(self=self, cls=type(self).__name__)
        return result

    @staticmethod
    def _as_guessed_type(value):
        """
        Perform appropriate type parsing on configuration files.

        Comma separated values are converted to tuples, where integers, floats
        and strings are converted to their corresponding Python native type.

        """

        def convert_type(val):
            val = val.strip()
            if val.isdigit():
                val = int(val)
            else:
                try:
                    val = float(val)
                except ValueError:
                    pass
            return val

        if "," in value:
            value = value.split(",")
            for ind, val in enumerate(value):
                value[ind] = convert_type(val)
            value = tuple(value)
        else:
            value = convert_type(value)
        return value

    def _get_option(self, section, name):
        """
        Get the value for the specified option under a specified section.

        Correctly removes line ending comments and provides a default return
        value.

        Parameters
        ----------
        section : str
            Section name.
        name : str
            Option name.

        """
        try:
            value = self.config[section][name] or self._INI_PARAMETERS[section][name]
        except KeyError:
            msg = (
                'The provided configuration section "{}" and item "{}" are '
                "not valid to ANTS.  See ants.config for further details."
            )
            raise KeyError(msg.format(section, name))
        if self._config.has_option(section, name):
            value = self._config.get(section, name)
            # Expand environmental variables
            value = os.path.expandvars(value)
            value = value.split("#")[0].strip()
            value = self._as_guessed_type(value)
            self.config[section][name] = value

    def parse_configuration(self, filename):
        """
        Parses a new configuration file.

        Entries in 'filename' override existing entries in the configuration,
        while entries not set remain unchanged from the previous state.

        Option to use a user defined temporary working directory.
        This is defined via the ANTS_TEMPORARY_DIR environment variable.

        Parameters
        ----------
        filename : str
            Name of the configuration file to read.

        """

        # Ignore file content until the first group (ConfigParser raises a
        # MissingSectionHeaderError otherwise).
        with open(filename, "r") as fh:
            cont = fh.readlines()
        cont = "".join(itertools.dropwhile(lambda x: not x.startswith("["), cont))
        self._config.read_file(io.StringIO(cont))

        # CHANGE THIS SO THAT WE LIST ALL "ants_*" groups and then iterate over
        # every single key under these groups (only ignoring the non-ants
        # groups).
        for section in self._config.sections():
            if section.startswith("ants"):
                # We ignore groups which aren't prefixed with "ants".
                for name in self._config.options(section):
                    self._get_option(section, name)

        if self["ants_logging"]["enabled"] == "True":
            _initialise_logger(level=self["ants_logging"]["level"])
        set_temporary_directory()

    def __getitem__(self, key):
        return self.config[key]

    def __setitem__(self, key, value):
        if key not in self.config:
            msg = "Unexpected configuration key: {}".format(key)
            raise ValueError(msg)
        self.config[key] = value


def _populate_config(config):
    for config_file in _DEFAULT_CONFIG_PATHS:
        try:
            config.parse_configuration(config_file)
        except IOError:
            continue


CONFIG = GlobalConfiguration()
_populate_config(CONFIG)


def _ensure_ants_cartopy_variable_not_set():
    if "ANTS_CARTOPY_CACHE" in os.environ:
        ants_cartopy_cache = os.environ["ANTS_CARTOPY_CACHE"]
        raise EnvironmentError(
            "The ANTS_CARTOPY_CACHE environment variable is no longer supported "
            "in ANTS from version 2.2. For guidance on configuring cartopy, see "
            "https://cartopy.readthedocs.io/stable/reference/config.html. "
            f"ANTS_CARTOPY_CACHE is currently set to '{ants_cartopy_cache}'. "
            "To use ants, unset ANTS_CARTOPY_CACHE."
        )
