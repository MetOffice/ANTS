# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
Decomposition in ants is achieved via :func:`decompose`.

ants decomposition can utilise the hardware available.  To that end, ANTS
respects scheduler configuration (SLURM, SPICE, LSF), utilising only the
hardware configured by the scheduler for the job.
Where no scheduler is used, the user may desire to configure ants themselves
(see :mod:`ants.config` for configuring ANTS_NPROCESSES).  Having both scheduler
and user configuration will cause an exception to be raised.

Additionally, decomposition is sensitive to the dataset(s) being decomposed.
To that end, configuration is necessary to tell ants how you wish source
datasets to be decomposed (see :class:`ants.config.GlobalConfiguration`).

Decomposition relies on being able to write temporary files to disk.
The temporary directory used can be configured by setting the ANTS_TEMPORARY_DIR
to a local directory capable of handling the volumes of temporary output data created
by the ANTS process you are running. (see: `ants.config`).

See :func:`ants.utils.cube.defer_cube`.

"""
import itertools
import logging
import os
from abc import ABCMeta, abstractmethod

import ants
import ants.utils
import dask
import dask.bag as db
import iris
import numpy as np
from ants.config import CONFIG

from . import stats

# List of _FILECleanup instances, referencing deferred data on disk
_TMP_FILES = {}
_LOGGER = logging.getLogger(__name__)


def _requested_processes():
    # Fetch the number of processes requested, ensuring that not both user and
    # scheduler define this parameter - we want to avoid over-specification as
    # well as the case where we don't respect the scheduler.
    specified = os.getenv("ANTS_NPROCESSES", "0")
    if specified.lower() == "max":
        specified = os.cpu_count()
    specified = int(specified)

    scheduler = (
        int(os.getenv("SLURM_NTASKS", 0))
        or int(os.getenv("PBS_NP", 0))
        or int(os.getenv("LSB_DJOB_NUMPROC", 0))
    )
    if specified and scheduler:
        msg = (
            "Decomposition configuration overspecified, both user and "
            "scheduler have specified the number of processes."
        )
        raise ValueError(msg)
    return scheduler or specified


def _mosaic_by_nsplits(iterable_shape, split):
    """
    Return a generator of slice objects that represent the requested
    subdivision.

    :param tuple iterable_shape: Shape to subdivide.
    :param tuple split: Specification of how many splits for each dimension.
    :return: Generator of tuples containing slice objects representing
        iterable_shape, split into the specified number of pieces.

    .. note::

        The shape of the last elements of each dimension may not be the same
        as those before them, as the split may not divide equally in that
        dimension.

    >>> slices = _mosaic_by_nsplits((3, 3), (1, 3))
    >>> print(list(slices))
    [(slice(0, None, 1), slice(0, 1, None)), (slice(0, None, 1), \
slice(1, 2, None)), (slice(0, None, 1), slice(2, None, 1))]

    """
    if len(iterable_shape) != len(split):
        raise ValueError(
            "Source shape with length {} does not match split "
            "length {}".format(len(iterable_shape), len(split))
        )

    for ind, in_shape, spl in zip(
        range(
            len(
                iterable_shape,
            )
        ),
        iterable_shape,
        split,
    ):
        msg = "{} shape at index {} has value {}, must be a positive integer."
        if in_shape <= 0:
            raise ValueError(msg.format("Source", ind, in_shape))
        if spl <= 0:
            raise ValueError(msg.format("Split", ind, spl))

    for it_shape, dim_split in zip(iterable_shape, split):
        if dim_split > it_shape:
            raise ValueError(
                "Cannot split our domain into more pieces than " "there are elements"
            )

    shape = tuple(
        [iterable_shape[dim] // split[dim] for dim in range(len(iterable_shape))]
    )

    subdomain = [
        [
            slice(itt * shape[dim], itt * shape[dim] + shape[dim])
            for itt in range(split[dim])
        ]
        for dim in range(len(shape))
    ]
    for sub_dim, dim_shape in zip(subdomain, iterable_shape):
        sub_dim[-1] = slice(sub_dim[-1].start, None, 1)
    return itertools.product(*subdomain)


class CallableMosaic(object, metaclass=ABCMeta):
    """
    Abstract mosaic generator factory.

    """

    @abstractmethod
    def __call__(self):
        """
        Mosaic generator.

        Called each time we require a slice through our sliceable object.
        Particularly beneficial where we are restricted by memory.

        :return: Mosaic generator of sliceable pieces.

        """
        pass

    @property
    def sliceable(self):
        return self._sliceable


def _guess_split(sources, target=None):
    # Arbitrarily choose 800MB as the appropriate chunk size.
    size_bytes = 800e6

    # Determine the array with the largest memory footprint and use that to
    # determine the split derived.
    source = sources
    if not isinstance(sources, iris.cube.Cube):
        source = sources[0]
    dtype = source.dtype
    largest_array = source

    if target:
        if not isinstance(target, iris.cube.Cube):
            target = target[0]
        dtype = np.promote_types(dtype, target.dtype)
        if (np.prod(target.shape) * np.nbytes[dtype]) > (
            np.prod(source.shape) * np.nbytes[dtype]
        ):
            largest_array = target

    # Account for additional non-horizontal dimensions by calculating
    # product of the non-horizontal dimension lengths.
    rem_shape = np.array(list(largest_array.shape))
    x, y = ants.utils.cube.horizontal_grid(largest_array)
    xd, yd = largest_array.coord_dims(x), largest_array.coord_dims(y)
    rem_shape[xd] = rem_shape[yd] = 1
    z_elements = np.prod(rem_shape)

    # Number of points which amount to size_bytes footprint.
    n_elements = int((size_bytes) / np.nbytes[dtype])

    # Split such that ~square extracts occur for likely optimisation of saving.
    shape = np.array(largest_array.shape)
    num_h = np.sqrt(n_elements / float(z_elements))
    x_split = np.ceil(shape[xd] / num_h).astype("int")
    y_split = np.ceil(shape[yd] / num_h).astype("int")

    ref_cube = target or source
    x, y = ants.utils.cube.horizontal_grid(ref_cube)
    xd, yd = ref_cube.coord_dims(x), ref_cube.coord_dims(y)
    if len(xd) > 1 or len(yd) > 1 or y_split.size > 1 or x_split.size > 1:
        msg = (
            "Currently, unable to guess a suitable decomposition split "
            "with sources containing grids which span multiple dimensions."
        )
        raise RuntimeError(msg)
    return {"split_x": x_split, "split_y": y_split}


def decompose(operation, sources, targets=None):
    """
    Decompose source(s) [and optional targets] and apply operation on each segment.

    Where only sources are provided, these sources are turned into mosaics.  Each
    mosaic piece then has the provided operation applied to it.
    If targets are also provided, then it is these targets that are turned
    into mosaics.  The sources which overlap each target mosaic piece then has the
    provided operation applied to it.
    See this module documentation on how decomposition is configured.

    Parameters
    ----------
    operation : ~collections.abc.Callable
        Operation to be computed on each decomposed piece within the
        decomposition framework, whether unary or binary.
    sources : One or more :class:`iris.cube.Cube`
        Cube(s) upon which the operation will be performed.
    targets : One of more :class:`iris.cube.Cube`, optional
        Target grid cube(s), utilised in binary operations.  See the note
        below on providing suitable targets.

    Returns
    -------
    : One or more :class:`iris.cube.Cube`
        Result from applying source and optional targets to the specified
        operation via the decomposition framework.

    Notes
    -----
    One of the following rules must apply for sources and targets provided:

    * len(sources) > 0 AND len(targets) in [0, 1]
    * len(sources) == 1 AND len(targets) > 1 AND (targets on identical
      horizontal grids and with equal shape)
    * len(sources) == len(targets)

    Where these conditions are not met, the relationship between source and
    target is ambiguous and an exception is thrown.  Under such circumstances,
    the user is referred to the :ref:`userguide <extended-usage>` where the
    'partial' library will allow arbitrary arguments/relationships to be
    utilised with the decomposition framework.

    """

    def gen_mosaics(sources, split):
        def gen_split(source, split):
            """
            Convert the dictionary 'split' to the source specific dimension
            mapping.

            """
            ss = np.array([1] * source.ndim)
            x, y = ants.utils.cube.horizontal_grid(source)
            xdims, ydims = source.coord_dims(x), source.coord_dims(y)
            ss[xdims] = split.get("split_x", None) or 1
            ss[ydims] = split.get("split_y", None) or 1
            return tuple(ss)

        if not isinstance(sources, iris.cube.Cube):
            res = [MosaicBySplit(src, gen_split(src, split)) for src in sources]
        else:
            res = MosaicBySplit(sources, gen_split(sources, split))
        return res

    processes = _requested_processes()

    pad_width = CONFIG["ants_decomposition"]["pad_width"]
    if pad_width is None:
        pad_width = 1

    decomposition = (
        MultiprocessingDomainDecompose(pad_width=pad_width)
        if processes > 1
        else DomainDecompose(pad_width=pad_width)
    )

    # We guess bounds on the full resolution dataset as guessing bounds on each
    # decomposed chunk can produce inconsistent results for circular datasets.
    # This is due to coordinates derived by a grid spacing that cannot be
    # represented exactly numerically (infinitely recurring decimal).
    # Bounds are guessed regardless of whether decomposition is actually used,
    # in order to keep as much processing identical as possible when decompose
    # is called.
    ants.utils.cube.guess_horizontal_bounds(sources)
    if targets:
        ants.utils.cube.guess_horizontal_bounds(targets)

    x_split = CONFIG["ants_decomposition"]["x_split"]
    y_split = CONFIG["ants_decomposition"]["y_split"]

    # x_split and y_split are None by default (set in config.py). If a user
    # wanted the splits guessed, both splits must be set to 'automatic'. The
    # same is true for 0, which is used if the user wants to disable the
    # decomposition framework. If both splits are > 0, the decomposition
    # framework will be used.

    if (x_split is None) ^ (y_split is None):
        msg = "If either x_split or y_split is set, both must be."
        raise RuntimeError(msg)

    if (x_split == "automatic") ^ (y_split == "automatic"):
        msg = "If either x_split or y_split is set to automatic, both must be."
        raise RuntimeError(msg)
    elif (x_split == 0) ^ (y_split == 0):
        msg = "If either x_split or y_split is set to 0, both must be."
        raise RuntimeError(msg)
    elif x_split == y_split == 0 or x_split is y_split is None:
        # No decomposition if both splits are set to 0 or if both splits are not
        # specified.
        if targets:
            result = operation(sources, targets)
        else:
            result = operation(sources)
        # The result is deferred even though decomposition is not used,
        # in order to keep as much processing identical as possible when decompose
        # is called.
        result = ants.utils.cube.defer_cube(result)
    else:
        # Use decomposition
        # Use splits from configuration.
        split = {"split_x": x_split, "split_y": y_split}

        if x_split == y_split == "automatic":
            # Setting both splits to automatic means that the splits are guessed.
            # Otherwise, the specified splits will be used.
            split = _guess_split(sources, targets)

        if targets:
            mosaics = gen_mosaics(targets, split)
            result = decomposition(operation, mosaics, sources)
        else:
            mosaics = gen_mosaics(sources, split)
            result = decomposition(operation, mosaics)

    return result


class MosaicBySplit(CallableMosaic):
    """
    Mosaic generator factory where mosaic piece size is determined by the
    number of pieces requested for the mosaic.

    For example:

    >>> import numpy as np
    >>> arr = np.array([[1, 2], [3, 4]])
    >>> splitter = MosaicBySplit(arr, (2, 1))
    >>> # Return our generator
    >>> slices = splitter()
    >>> print(list(slices))
    [array([[1, 2]]), array([[3, 4]])]

    """

    def __init__(self, sliceable, split):
        """
        Mosaic generator factory for the given sliceable with specified
        target shape.

        Parameters
        ----------
        sliceable: :term:`array_like`
            Object with shape property and numpy style indexing.  Mosaic
            pieces correspond to a pieces of this given sliceable object.
        split : tuple
            Specified how each dimension should be split.
        """
        self._split = split
        self._sliceable = sliceable
        _LOGGER.info("{} split: {}".format(self.__class__.__name__, self._split))

    @property
    def split(self):
        """tuple : Number of split corresponding to each dimension."""
        return self._split

    def __call__(self):
        _slice_ref = _mosaic_by_nsplits(self._sliceable.shape, self.split)
        for tile in _slice_ref:
            yield self._sliceable[tile]


class _FileCleanup(object):
    """
    File cleanup class, where it tries to delete the provided file when the
    object is deleted.

    """

    def __init__(self, filename):
        self._filename = filename

    # Reference to os in case it is garbage collected before this class
    # instance.
    remove = os.remove

    def __del__(self):
        try:
            self.remove(self._filename)
        except OSError:
            pass

    def __str__(self):
        return self._filename

    def __repr__(self):
        return "_FileCleanup({})".format(self._filename)


def _operation_wrap(operation):
    # This function allows us to wrap user operations, providing deferred
    # return etc.
    if hasattr(operation, "func"):
        # Support for functools.partial
        operation_name = operation.func.__name__
    elif hasattr(operation, "__class__"):
        # Support for callable classes
        operation_name = operation.__class__.__name__
    else:
        # Support for functions
        operation_name = operation.__name__

    def wrapped_operation(*args, **kwargs):
        # source-target cube shapes
        _LOGGER.info(
            [
                "source_{}_{}.shape: {}".format(i, cube.name(), cube.shape)
                for i, cube in enumerate(args[0])
            ]
        )
        if len(args) > 1:
            msg = [
                "target_{}_{}.shape: {}".format(i, cube.name(), cube.shape)
                for i, cube in enumerate(args[1])
            ]
            _LOGGER.info(msg)

        # Convert list of cubes to a single cube to improve enduser UI
        args = list(args)
        for ind in range(len(args)):
            if len(args[ind]) == 1:
                args[ind] = args[ind][0]

        with stats.TimeIt() as timer:
            res = operation(*args, **kwargs)
        _LOGGER.info('operation: "{}" took {}'.format(operation_name, timer.time_taken))

        res = ants.utils.cube.defer_cube(res)
        return res

    return wrapped_operation


class DomainDecompose(object):
    """
    Domain decompose an operation for a given cube for both unary and binary
    operations.

    """

    def __init__(self, pad_width=1):
        """
        Create a decomposable cube wrapper to which we can apply unary and
        binary operations.

        Parameters
        ----------
        pad_width: int
            Pad the slices of the extracted source domain by the specified
            number of cells. Default is 1.

        """
        self.pad_width = pad_width
        self._sources = None
        _LOGGER.info("{} framework utilised".format(self.__class__.__name__))

    def __call__(self, operation, mosaics, sources=None):
        """
        Perform the provided operation over each decomposed piece.

        Parameters
        ----------
        operation : ~collections.abc.Callable
            Binary or unary operation on which to apply over each decomposed
            piece.
        mosaic : :class:`CallableMosaic` object
            Callable which returns a generator of cubes.
        sources : One or more :class:`iris.cube.Cube`, optional
            Source cube(s), where an extracted overlap is performed with each
            target piece in order to perform our binary operation.

        """
        if (
            mosaics
            and not hasattr(mosaics, "__iter__")
            and hasattr(mosaics, "__call__")
        ):
            mosaics = [mosaics]
        if isinstance(sources, iris.cube.Cube):
            sources = [sources]

        self._operation = operation
        self._mosaics = mosaics
        # Decompose the target and optionally a source.
        self._sources = sources

        # Generate suitable arguments for starfunc (generalised map)
        src_generator = self.src_generator
        if src_generator is not None:
            args = [src_generator, self.mosaic_generator]
        else:
            args = [self.mosaic_generator]

        # Perform provided operation over each decomposed piece
        results = self._run(_operation_wrap(operation), args)

        # Put these results back together
        cubes = self._gather(results)
        return cubes

    def _flatten(self, nlist):
        # Shallow flatten - for supporting operators that return 1 or more
        # cubes.
        if isinstance(nlist[0], list):
            return list(itertools.chain.from_iterable(nlist))
        else:
            return nlist

    def _gather(self, results):
        results = self._flatten(results)
        cubes = iris.cube.CubeList(results)

        # Associate our file cleanup objects
        for cube in cubes:
            # Global and local storage of filecleanup is necessary when
            # supporting both serial and multi-process running.
            # This must be performed here in the controlling process so that
            # temporary data persists until the end of the session.
            if id(self) in _TMP_FILES:
                _TMP_FILES[id(self)].append(_FileCleanup(cube._fh))
            else:
                _TMP_FILES[id(self)] = [_FileCleanup(cube._fh)]
            # Alternative approach is to allow the cleanup object only to
            # persist as long as that specific cube instance.
            # cube.lazy_data()._fh = _FileCleanup(cube._fh)

        cubes = cubes.concatenate()
        # After concatenation, ensure that we retain the circular attribute if
        # appropriate.
        ants.utils.cube.derive_circular_status(cubes)

        if len(cubes) == 1:
            cubes = cubes[0]
        return cubes

    def _run(self, operation, args):
        _LOGGER.info(stats.sys_stat())
        _LOGGER.info(stats.proc_stat())
        return list(map(operation, *args))

    @property
    def mosaic_generator(self):
        """~collections.abc.Iterator : An iterator over all the mosaic pieces."""
        return zip(*[mosaic() for mosaic in self._mosaics])

    def source_piece_generator(self, source, mosaic):
        """Create a generator for source pieces that overlap with target pieces.

        This method uses ants.ExtractConstraint to extract source pieces that overlap
        with each target piece returned by the mosaic generator. The region extraction
        uses the ``pad_width`` provided when initialising the class instance.

        Parameters
        ----------
        source: iris.cube.Cube
            The source cube to be split into pieces
        mosaic: ~collections.abc.Iterable[iris.cube.Cube]
            Iterable of target pieces for source to overlap

        Returns
        -------
        ~collections.abc.Generator[iris.cube.Cube]
            Pieces of the source cube which overlap with each target cube in the mosaic
        """
        return (
            source.extract(
                ants.ExtractConstraint(tgt, fix_period=False, pad_width=self.pad_width)
            )
            for tgt in mosaic
        )

    @property
    def src_generator(self):
        """
        list of :class:`~iris.cube.Cube` : The source which overlaps each
        decomposed target piece.

        """

        source_generator = None
        if self._sources is not None:
            if len(self._mosaics) == 1:
                source_generator = zip(
                    *[
                        self.source_piece_generator(src, self._mosaics[0]())
                        for src in self._sources
                    ]
                )
            elif len(self._sources) == 1 and len(self._mosaics) > 1:
                cubes = [mosaic.sliceable for mosaic in self._mosaics]
                same_grid = ants.utils.cube.is_equal_hgrid(cubes)
                if not same_grid:
                    msg = (
                        "Ill-defined relationship between 1 source and "
                        "multiple targets, where those targets aren't"
                        "defined on the same grid.  See the user guide "
                        "for advanced usage."
                    )
                    raise RuntimeError(msg)
                source_generator = zip(
                    *[
                        self.source_piece_generator(src, self._mosaics[0]())
                        for src in self._sources
                    ]
                )
            elif len(self._sources) != len(self._mosaics):
                msg = (
                    "Ill-defined relationship between number of sources "
                    "and targets.  See the user guide for advanced usage."
                )
                raise RuntimeError(msg)
            else:
                source_generator = zip(
                    *[
                        self.source_piece_generator(src, mosaic())
                        for src, mosaic in zip(self._sources, self._mosaics)
                    ]
                )
        return source_generator

    def _cleanup(self):
        """
        Clear the cache generated as a result of this decomposition object.

        The cache is automatically cleared as part of garbage collection of the
        global TMP_FILES object (which holds all the _FileCleanup objects).
        This method enables the developer to clear the cache associated with
        the decomposition object for debugging purposes and is not used by the
        class itself.

        """
        _TMP_FILES.pop(id(self))


class MultiprocessingDomainDecompose(DomainDecompose):
    """
    Domain decompose an operation in parallel for a given cube for both unary
    and binary operations.

    """

    def _run(self, operation, args):
        num_workers = _requested_processes()
        _LOGGER.info(f"{num_workers} workers utilised")
        # We convert to a list as dask hangs indefinitely otherwise...
        parameters = list(zip(*args))
        with dask.config.set(
            {"multiprocessing.context": "fork"}, num_workers=num_workers - 1
        ):
            bag = db.from_sequence(parameters)
            results = bag.starmap(operation).compute()
        return results
