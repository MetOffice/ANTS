.. include:: common.txt
.. highlight:: console

***************
Installing ANTS
***************

Prerequisites
=============

In order to install and get ANTS running in full you will need the following:

* An installed version of `conda <https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html>`_
  and some `familiarity <https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html>`_ with it
* A local install of `mule and shumlib
  <https://code.metoffice.gov.uk/doc/um/mule/latest>`_ - talk to your local
  UM support team if you need support with this
* `Rose <http://metomi.github.io/rose/doc/html/index.html>`_ and
  `cylc <https://cylc.github.io/>`_ for running rose-stem test workflows (requires cylc
  version >= 8.6.0)

Depending on your local site configuration, it may be necessary to unset the
``LD_LIBRARY_PATH`` environment prior to running the following conda commands.
The symptom that indicates that the ``LD_LIBRARY_PATH`` is causing an issue is
that usage of ESMPy (i.e. using the ``ConservativeESMF`` regridding scheme)
causes a ``PIOMissing`` error.

Installing conda dependencies
=============================

To start with you will need to checkout a working copy of ANTS as::

   $ git clone git@github.com:MetOffice/ANTS.git
   $ cd ANTS

To install the dependencies for a specific release of ANTS, use the
``environment.lock`` file to create an environment with the dependency
versions expected for that release::

    $ conda create -p <path/to/install/ants_env> --file environment.lock

For development work, you may want the most recent packages available, with
only key packages fixed to a specific versions. In that case, use the
``environment.yml`` file to create the environment::

    $ conda env create -n <ants_env> -f environment.yml

In either case, you should then be able to activate the resulting environment
by running::

    $ conda activate <ants_env>

Installing ANTS into your environment
=====================================

With your conda environment created, you can then install ANTS into it. If it
is not already activated, then run::

    $ conda activate <ants_env>

Then, from the top directory of your checked out working copy of ANTS, run::

    $ python -m pip install .

Alternatively, if you want to make sure you are only using the versions of packages
specified in your environment, or are working on a platform without internet access,
you can use the ``--no-build-isolation`` option to pip as follows::

    $ python -m pip install --no-build-isolation .

For development work, you may want to install ANTS in editable mode::

    $ python -m pip install --editable .

Configuring Mule
----------------

ANTS requires a local installation of |Mule|.  Mule's bin directory must be
added to the PATH and the lib directory added to the PYTHONPATH.  This is
required for using the UM spiral search, loading UM format ancillaries
(i.e. as defined in F03), or saving UM format ancillaries; but can be omitted
for the rare use cases where those features are not needed.

.. _quick-verification:

Quick verification
------------------

A quick verification that the installation has completed can be done by
activating the environment (if it's not already active) and running::

    $ ants-version

If everything has worked correctly, the returned path should point inside the
newly created conda environment for a stable installation, or to the working
copy of ANTS for a developer (editable) installation.

Confirming ANTS Installation
============================

If you have opted to build an environment and install ANTS into it, more
thorough verification can be done by running the unittests.

To run the tests in an installation, run the :ref:`quick verification
<quick-verification>` command from the previous section to get the path for
your ANTS installation. Then ``cd`` into the directory that contains the ants
installation (i.e. the directory above the ``ants`` directory) and run::

    $ python -m pytest ./ants

Around 7% of the tests will error or fail due to missing data files.  For a
more thorough test, from the directory that contains the ants installation,
use::

    $ cp -r <working/copy>/lib/ants/tests/resources ./ants/tests/.
    $ cp <working/copy>/pyproject.toml ./ants/.

The unittests can then be run as::

    $ python -m pytest -c ./ants/pyproject.toml ./ants

All unittests should then pass.  After running the tests, the
``./ants/tests/resources`` directory and ``./ants/pyproject.toml`` file should
be removed.

Running the test workflow
=========================

.. note::
    The test workflow requires cylc at a version >= 8.6.0

The ``rose-stem`` directory contains a cylc workflow that runs unittests,
integration tests, checks code style and builds documentation. To run the full
workflow, use::

    $ cylc vip ./rose-stem -z group=all

The usual ``cylc vip`` command line options can also be passed, for example to
name the workflow, use ``-n <worflow_name>``.

A subset of the workflow can be run by replacing ``all`` with a different group
or groups, e.g. ``-z group=unittests,documentation`` to run just the unit
tests and build the documentation.

Installing KGOs
===============

In order to run the rose stem test workflow, it is necessary to create a set
of site specific KGO files.  Please see the :doc:`managing KGOs </tutorial_KGO>`
tutorial for details.
