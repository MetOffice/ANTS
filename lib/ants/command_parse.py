# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import argparse
import inspect
import logging
import os
import sys

import ants
from ants.exceptions import (
    InvalidOutputPathException,
    TimeConstraintMissingException,
    TimeConstraintUnorderedException,
)

_LOGGER = logging.getLogger(__name__)


class AntsArgParser(argparse.ArgumentParser):
    """
    Standardised ancillary commandline interface.
    """

    def __init__(self, target_lsm=False, target_grid=False, time_constraints=False):
        """
        Parse command-line arguments and options.

        The following arguments represent those common to all ancillary
        applications::

            sources <SOURCE1> <SOURCE2> ... <SOURCEN>     Source data path(s).
            --output <OUTPUT>, -o <OUTPUT>                Output filepath
            --ants-config <ANTS_CONFIG>                   Configuration path.

        Additionally, there are standardised optional arguments and these are
        activated by passing the relevant keyword argument.  See 'Parameters'
        below for further detail on these standardised interfaces to ancillary
        generation applications.  See :mod:`ants.config` for further details
        on ANTS run-time configuration of ANTS.

        Parameters
        ----------
        target_lsm : :obj:`bool`, optional
            Standardised optional argument.  When True, the user is required
            to provide a land binary mask via a ``--target-lsm`` keyword argument
            followed by the path to the land sea mask.
        target_grid : :obj:`bool`, optional
            Standardised optional argument.  When True, the user is required
            to provide a target grid file via a ``--target-grid`` keyword argument
            followed by the path to the grid file.
        time_constraints : :obj:`bool`, optional
            Standardised optional argument. When True, the user is able
            to provide two keyword arguments to constrain the search data by time:
            a "--begin" keyword argument which must be earlier or equal to the
            "--end" keyword argument. Both should be provided as years in the
            format YYYY.

        Note
        ----
        This class behaves in the same manner as the
        :class:`argparse.ArgumentParser` class.  Adding additional commandline
        arguments can be done in the standard way (see :mod:`argparse`).  Two
        additional types are provided that can be used with the 'type'
        argument of :meth:`argparse.ArgumentParser.add_argument`:
        :func:`ants.config.filepath_readable` and
        :func:`ants.config.dirpath_writeable`.


        This choice should be on the basis that the newly proposed interface is
        necessarily not common to the UI of other ancillary applications.
        Often this can be the case for pre-processing applications.

        """
        # Get the module documentation from that which instantiated the
        # argparser.
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        doc = mod.__doc__

        super(AntsArgParser, self).__init__(
            description=doc, formatter_class=argparse.RawDescriptionHelpFormatter
        )
        self.add_argument(
            "sources",
            type=ants.config.filepath_readable,
            nargs="+",
            help="Source data path(s).",
        )

        target_obj = self

        # Arguments change below depending on whether target_lsm, target_grid,
        # or both are requested.  land-threshold is needed with target_lsm
        # whether or not target_grid is asked for:
        if target_lsm:
            self.add_argument(
                "--land-threshold",
                type=float,
                required=False,
                help="Land fraction threshold for converting "
                "land fraction (where provided) to a landsea mask.",
            )

        if target_lsm and target_grid:
            group = self.add_mutually_exclusive_group()
            lsm_help = (
                "Path to the land sea mask. "
                "If provided the file is used to define both "
                "the target grid "
                "and the land sea mask. The land sea mask is "
                "used in the nearest neighbour fill of missing data "
                "for land only "
                "or ocean only fields.  "
                "``--target-lsm`` or ``--target-grid`` should be provided but "
                "not both."
            )

            group.add_argument(
                "--target-lsm", type=ants.config.filepath_readable, help=lsm_help
            )

            grid_help = (
                "Path to the target grid file(s).  "
                "The grid files can be CAP horizontal namelists, "
                "UM vertical namelists or any file type supported by "
                "iris.load (NetCDF, pp, Ancillary).  "
                "If using more than one grid file then separate "
                "the file names with a space.  "
                "``--target-lsm`` or "
                "``--target-grid`` should be provided but not both."
            )
            group.add_argument(
                "--target-grid",
                type=ants.config.filepath_readable,
                nargs="+",
                help=grid_help,
            )
        elif target_lsm:
            self.add_argument(
                "--target-lsm",
                type=ants.config.filepath_readable,
                required=target_obj is self,
                help="Path to the land sea mask.",
            )
        elif target_grid:
            target_obj.add_argument(
                "--target-grid",
                type=ants.config.filepath_readable,
                required=target_obj is self,
                nargs="+",
                help="Path to the target grid file.",
            )
        self.add_argument(
            "--output",
            "-o",
            type=ants.config.dirpath_writeable,
            required=True,
            help="Output filepath, which must be different from the source "
            "input file(s).",
        )
        self.add_argument(
            "--ants-config",
            type=ants.config.filepath_readable,
            help="Configuration path.  See ants.config",
        )
        self.add_argument(
            "--netcdf-only",
            action="store_true",
            help="Only write out a netCDF file.",
            required=False,
        )
        if time_constraints:
            self.add_argument(
                "--begin",
                "-b",
                type=ants.config.formatted_time,
                required=False,
                help="Year to start the processing in the format 'YYYY' e.g. '1990'.",
            )
            self.add_argument(
                "--end",
                "-e",
                type=ants.config.formatted_time,
                required=False,
                help="Year to end the processing in the format 'YYYY' e.g. '2010'. "
                "For a single year of data, this should be the same as the argument "
                "given to the ``--begin`` argument.",
            )
        try:
            self._optionals.title = "Additional arguments"

        except AttributeError:
            # Argparse may have changed its internal structure - we'll be
            # seeing the default title for groups of arguments.
            pass

    def parse_args(self, args=None, namespace=None):
        """
        Return parsed commandline arguments according to the object
        specification.

        Output filepaths are verified for write permissions.
        Input filepaths are verified for read permissions.
        Optional time constraints are verified if supplied that
        both exist and with the earlier date first.
        This ensures that exceptions are raised as soon as possible.

        Note
        ----
        The ants configuration is populated where an optional --ants-config has
        been provided during the parse.

        """
        args = super(AntsArgParser, self).parse_args(args, namespace)

        dirpath = os.path.dirname(args.output)
        filename = os.path.basename(args.output)
        args.output = os.path.join(ants.config._expand_path(dirpath), filename)
        if args.ants_config:
            ants.config.CONFIG.parse_configuration(args.ants_config)
        for x in args.sources:
            if os.path.abspath(x) == os.path.abspath(args.output):
                raise InvalidOutputPathException()
        try:
            if (args.begin and not args.end) or (args.end and not args.begin):
                raise TimeConstraintMissingException()
            if (args.begin is not None) and (args.end is not None):
                if args.end < args.begin:
                    raise TimeConstraintUnorderedException()
        except AttributeError:
            _LOGGER.info("All data included in result - no time constraints are used.")
        _LOGGER.info("ANTS run-time configuration: {}".format(ants.config.CONFIG))
        _LOGGER.info("CLI: {}".format(args))
        _LOGGER.info("sys.argv: {}".format(sys.argv))
        return args
