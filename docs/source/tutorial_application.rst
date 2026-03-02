.. meta::
   :description lang=en: Tutorial on developing ANTS based applications
   :keywords: contribute, ancillary-file-science, application, development, tutorial
   :property=og:locale: en_GB

.. _writing-applications:


Writing an ANTS based application
=================================

The ANTS library provides a toolkit of functionality common to many ancillary
generating applications. The user-written applications used for the standard
model configurations within the Momentum partnerhsip are held under the
:ancillary-file-science:`ancillary-file-science<>` project (must be signed in
to an account with appropriate GitHub permissions for access to that link).

An application will usually contain code to carry out the following steps:

1. Read input arguments, such as input and output file names, target
   grid definition.
2. Load the data from the input files.
3. Process (e.g regrid) the source data to produce the ancillary field(s).
4. Save the data to the output file.

For each of these steps, the ANTS library contains code to assist with common
operations. In particular, :mod:`ants.command_parse` provides a common
commandline interface, which is important to use to ensure a consistent user
interface (UI) between all applications, and :mod:`ants.io.save` contains
routines for saving ancillary data to common fileformats. As ANTS is based on
Iris, you can also use any of the available Iris functionality to process
your data.

In the tutorial here, we will write an ancillary generating application that
covers all steps of the :doc:`ancillary_generation_pipeline`. In real use
cases though, it is often preferable to write multiple separate applications,
connected via a workflow, to avoid writing monolithic, complex, and expensive
to run individual applications. See
:ancillary-file-science:`ancillary-file-science<>` and the associated
rose-stem workflow for examples of such implementations and breakdowns.

As prerequisites for carrying out this tutorial we assume:

* Familiarity with `Python <https://www.python.org/>`_
* Familiarity with `Iris <https://scitools-iris.readthedocs.io/en/stable/>`_
* Access to and ability to activate an environment with ANTS and its dependencies installed

And for the next steps, familiarity with:

* `Pytest <https://docs.pytest.org/en/stable/>`_
* `Rose <http://metomi.github.io/rose/doc/html/index.html>`_ and `Cylc <https://cylc.github.io/>`_

Initial setup
-------------

To get started with you will want to check out a copy of
:ancillary-file-science:`ancillary-file-science<>` and create a branch where
you will be working on your implementation. You will also need an environment
active with ANTS installed into it so that you can carry out interactive
development and testing of your application.

Create App Directory
--------------------

Having got your working copy of your branch checked out, we need to create our
application in the appropiate place. Ancillary generation applications live in
the "Apps" directory of ``ancillary-file-science``. For now, create a
directory under "Apps" called "Tutorial", and within that create an
"ancil_tutorial.py" where we will be carrying out the coding exercise in this
tutorial.

In your editor of choice, open up the ancil_tutorial.py file and update it so
it contains the following:

.. code-block:: python

    """
    Tutorial application
    ********************

    This application was written to carry out the application development
    tutorial in ANTS.

    The application does the following:
    * Loads source and target cubes from the provided filepaths,
    * Regrids the source data to the target grid using an area weighted regrid.
    * Adds 1.0 to every data value,
    * Saves the result to the specified output file path as NetCDF and, optionally,
      also as a ancillary file.

    The application implements a few features of ANTS that are common to
    ancillary applications.
    """
    import ants
    import ants.regrid
    import iris
    from ants import load_cube
    from ants.io.save import ancil, netcdf


    def load_data():
        return

    def add_one():
        return

    def regrid_area_weighted():
        return

    def _get_parser():
        return

    def main():
        return

    if __name__ == "__main__":
        main()

This provides us with an initial skeleton from which we will be working. Notice
how we have set up placeholders for the majority of the steps we want our app
to carry out - we always aim to break down our ancillary generation routines
into their constituent parts and avoid "monolithic" main functions containing
all the operations wherever possible.

Add Arg Parser
--------------

ANTS provides a common command line arguments parser via
:mod:`ants.command_parse` for use in ancillary applications to provide
arguments such as:

* Source filepath(s)
* Output filepath
* ANTS configuration filepath
* Target grid or target landseamask filepath
* NetCDF-only save option

This helps ensure a consistent interface across ANTS based applications and
provides a standard entry point for options typically required by them. The
:py:class:`ants.AntsArgParser` class used for this can be extended to
include application-specific arguments, as required, by using the
:meth:`argparse.ArgumentParser.add_argument` method. Here, we will use the out-the-box parser.

In your previously created ``ancil_tutorial.py`` file, update
``_get_parser():`` as follows:

.. code-block:: python

    def _get_parser():
        """Get ANTS argument parser."""
        parser = ants.AntsArgParser(target_grid=True)
        return parser

and also update the ``if __name__ == "__main__":`` as:

.. code-block:: python

    if __name__ == "__main__":
        args = _get_parser().parse_args()
        main()

Save your changes and you can then inspect the interface by running
``python ancil_tutorial.py --help``. If all has been done correctly then you
should see help text printed to the command line showing the various options
you can supply via the ``AntsArgParser``.

Notice that when we create our parser we are using the ``target_grid=True``
option. This is because we intend to supply the application with a target grid
for regridding to later in our implementation.

Add File Loading
----------------

For our next step, we are going to need some data. For this, we will be using
the ``sample_source.nc`` and ``sample_target.nc`` files stored in the
``rose-stem/sources`` directory of ancillary-file-science. Take a moment to
inspect and familiarise yourself with these files using your netCDF tool of
choice e.g.  ``ncdump -h <file>`` to inspect the contents. As we go about
implementing our application we will use ``print()`` statements to provide
debugging to confirm what we have done is what we expect. You should see
outputs consistent with what you saw inspecting the file in your chosen netCDF
tool.

To load our source data into our application we will make use of the
``load_cube`` routine from ANTS. Update the ``load_data()`` routine as follows:

.. code-block:: python

    def load_data(source_path, target_path):
        """
        Return cubes obtained from loading the `source` and `target` files.

        Parameters
        ----------
        source_path : str
            Filename from which to read source data.
        target_path : str
            Filename from which to read target data.
        Returns
        -------
        tuple[:class:`~iris.cube.Cube`, :class:`~iris.cube.Cube`]
            The loaded `surface_altitude` and `target` cubes.
        """

        surface_altitude_constraint = iris.NameConstraint(standard_name="surface_altitude")
        surface_altitude_cube = load_cube(source_path, surface_altitude_constraint)

        target_cube = load_cube(target_path)

        return surface_altitude_cube, target_cube

and update the ``main()`` routine as:

.. code-block:: python

    def main(source_path, target_path):
        surface_altitude, target = load_data(source_path, target_path)
        print(surface_altitude)
        print(target)
        return

and ``if __name__ == "__main__":`` as:

.. code-block:: python

    if __name__ == "__main__":
        args = _get_parser().parse_args()
        main(args.sources, args.target_grid)

Looking at our ``load_data`` routine we've done a few things worth noting.
Often, source files will contain more than one field, or we want to make sure
we are only loading specific fields (as opposed to whatever is in there). To do
this we make use of Iris constraints. Here we want to specifically load the
surface altitude fields.

Run your application as: ``python ancil_tutorial.py /path/to/sample_source.nc --target-grid /path/to/sample_target.nc -o output.nc``
and you should see details of the loaded iris cubes printed to screen. N.B. we
have had to supply the ``-o output.nc`` option as the interface requires it,
even though we have not yet implemented code to save the file itself.

Add Regridding
--------------

Assuming no further processing of our source is necessary, the next thing we
will want to do is to put that data on our target model grid, as supplied to
our application via the ``--target-grid`` option. To do this we will be using
the ANTS general regrid interface. Update the ``def regrid_area_weighted():``
section so it is as follows:

.. code-block:: python

    def regrid_area_weighted(source, target):
        """Regrid data from `source` cube to `target` grid.

        Uses the ANTS area-weighted regrid scheme.

        Parameters
        ----------
        source : :class:`~iris.cube.Cube`
            Cube containing the data to be regridded.
        target : :class:`~iris.cube.Cube`
            Target cube containing the destination grid.

        Returns
        -------
        :class:`~iris.cube.Cube`
            Data from `source` regridded to `target`.
        """
        scheme = ants.regrid.GeneralRegridScheme(horizontal_scheme="AreaWeighted")
        return source.regrid(target, scheme)

This will take in a source code and use the ANTS general regrid AreaWeighted
routine to regrid it to the provided target grid.

We will then integrate this into our main routine by updating it as follows:

.. code-block:: python

    def main(source_path, target_path):
        surface_altitude, target = load_data(source_path, target_path)
        print("Before regrid:")
        print(surface_altitude)
        print(target)
        regridded_surface_altitude = regrid_area_weighted(surface_altitude, target)
        print("After regrid:")
        print(regridded_surface_altitude)
        return

Run your application as before. Look at the outputs printed to screen and you
should see that the resolution of the regridded surface altitude is different
from the original source data.

Add Some Processing
-------------------

With data on our target grid we will then likely want to do some processing.
Here, we will use our ``add_one()`` routine to do this. We'll use this routine
to take in a cube, and return the result of adding 1.0 to the data in there.
Update it as follows:

.. code-block:: python

    def add_one(cube):
        """
        Return a modified cube.

        Returned cube is the same as the original cube, except 1.0 is added to
        each data value.  Original cube is not modified.

        Note
        ----
        This function operates on a single cube, not a CubeList.

        Parameters
        ----------
        cube : :class:`~iris.cube.Cube`
            Cube to add 1.0 to.
        Returns
        -------
        :class:`~iris.cube.Cube`
            The cube that has had 1.0 added to it.

        """
        result = cube.copy(cube.core_data() + 1.0)
        return result

We will make use of this in our main function by applying it to the sum of our
two regridded fields. Update ``main()`` so it looks like this:

.. code-block:: python

    def main(source_path, target_path):
        surface_altitude, target = load_data(source_path, target_path)
        print("Before regrid:")
        print(surface_altitude)
        print(target)
        regridded_surface_altitude = regrid_area_weighted(surface_altitude, target)
        print("After regrid:")
        print(regridded_surface_altitude)
        result = add_one(regridded_surface_altitude)
        result.attributes["STASH"] = "m01s00i033"
        print("Results cube:")
        print(result)
        return

Notice that we have also updated the STASH attribute on the cube via the
``result.attributes["STASH"] = "m01s00i033"`` operation. In order to generate
a valid UM ancillary file we need an associated STASH code as this is the only
identifier in the file as to what the data is, both to the model and any user
inspecting the file.

As before, run your program and make sure everything is as expected.

Save a File
-----------

The final thing to add is saving the results of our processing.
By default we recommend always saving out a copy of the processed data in
netcdf in addition to any other formats. For saving, we will make use of the
routines in :mod:`ants.io.save` we imported earlier - ``ancil`` and ``netcdf``.

Firstly, lets update our ``if __name__ == "__main__":`` section to pass through
the argument to main for what file to save to, along with whether we want to
only save in netcdf (a convention we follow across ancillary apps where
applicable) as:

.. code-block:: python

    if __name__ == "__main__":
        args = _get_parser().parse_args()
        main(
            args.sources,
            args.target_grid,
            args.output,
            args.netcdf_only,
        )

We will now update our ``main()`` section to take these arguments and to run
the savers. While we are in there we will also remove the debug print
statements, add some comments, and put in a docstring.
Update your ``main()`` section to look like this:

.. code-block:: python

    def main(source_path, target_path, output_path, netcdf_only):
        """
        Regrid a field, add 1 to the data, and save
        the result to a file.

        Parameters
        ----------
        source_path : str
            Filename from which to read source data.
        target_path : str
            Filename from which to read target grid.
        output_path : str
            Filename to write results to.
        netcdf_only : bool
            If True, only write output to netCDF file.
            If False, write output to both netCDF and
            ancillary files.

        Returns
        -------
        :class:`~iris.cube.Cube`
            The processed cube.

        """

        # Load in the source data and target grid
        surface_altitude, target = load_data(source_path, target_path)

        # Regrid surface_altitude to the target grid
        regridded_surface_altitude = regrid_area_weighted(surface_altitude, target)

        # Process the data
        result = add_one(regridded_surface_altitude)
        result.attributes["STASH"] = "m01s00i033"

        # Always save to netcdf file
        netcdf(result, output_path)

        # Also save to ancillary file unless the '--netcdf-only'
        # command line option has been specified
        if not netcdf_only:
            ancil(result, output_path)

        return result

Save your changes and try out your code. Experiment with the ``--netcdf-only``
option and different filenames for your output. You can use mule to inspect
the ancil file to make sure it is how you expect and whatever your goto netcdf
tool is to inspect the netcdf file.

Next Steps
----------

With your application now written, your next step would be to add pytest style
unittests for the routines in the application. These would be stored in a
tests subdirectory of the ``Apps/Tutorial`` directory you created earlier. We
will not go into detail of doing that here, but because we broke down our code
into constituent parts rather than leaving it all under ``main()`` we are more
easily able to test the code. With unittests written, your final step would be
to integrate your new application into the rose-stem framework in
``ancillary-file-science``, providing a representative workflow with some
cutdown/representative/synthetic low resolution data. For examples of adding
unittests and up-to-date way of implementing rose-stem testing, see the
example "Sample" application in
:ancillary-file-science:`ancillary-file-science<>`.

For the latest guidance on what would be expected from a finalised
application visit the ANTS Working Practices page.

Summary
-------

From the above, you should now have created a application that:

* Implements the ANTS argument parser
* Loads in some specified data from a file
* Loads in a target grid
* Regrids data to a target grid using an ANTS regridder
* Carries out some data processing
* Saves data to netcdf and ancil file formats, with the option to save netcdf only

And if you carried out the Next Steps:

* Is unittested
* Is tested under rose-stem

Advanced Usage
--------------

The tutorial provided above is a deliberately small scale example with low
resolution synthetic data and a low resolution target grid. In real world usage
source datasets are often significant in size and target grids contain many
more points than in the example here. As a result you may find that some of
the operations carried out consume too many resources for the platforms being
run on, or that the operations take too long for your needs. In that situation,
the author will need to look into optimisation of their codes. ANTS provides
some out-the-box support for this via the :mod:`ants.decomposition` framework
for splitting up and parallelising operation, noting that care will be needed
to ensure its usage is appropriate for the codes being parallelised.

Finally, it is also always worth taking a look at the existing ancillary
generation applications in :ancillary-file-science:`ancillary-file-science<>`
to see what has been done before. It may be that related implementations
already exist for what you are intending to do, or that ideas for how to use
parts of the :doc:`API docs <lib/modules>` in your processing chain.
