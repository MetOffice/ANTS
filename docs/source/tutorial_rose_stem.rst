.. meta::
   :description lang=en: Tutorial on running the test workflow
   :keywords: KGO, rose stem, development, tutorial
   :property=og:locale: en_GB

.. highlight:: console

Running the rose stem test workflow
===================================

The ``rose-stem`` directory contains a `cylc`_ workflow that runs unittests,
integration tests, checks code style and builds documentation.

.. _cylc: https://cylc.github.io/cylc-doc/stable/html/index.html

Prerequisites
-------------

- The test workflow requires cylc at a version >= 8.6.0
- Sources must be pre-generated, see :doc:`/tutorial_sources`
- Known good outputs (KGOs) must be pre-generated, see :doc:`/tutorial_KGO`

Running
-------

To run the full workflow, run the following command from the top level of a
working copy of ANTS:

.. versionchanged:: 3.0.0
   The rose stem workflow is now run via ``cylc vip`` rather than ``rose stem``.

.. code-block::

  $ cylc vip ./rose-stem -z group=all

The usual ``cylc vip`` command line options can also be passed, for example to
name the workflow, use ``-n <worflow_name>``.

A subset of the workflow can be run by replacing ``all`` with a different group
or groups, e.g. ``-z group=unittests,documentation`` to run just the unit
tests and build the documentation.
