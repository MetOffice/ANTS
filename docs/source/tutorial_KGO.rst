.. meta::
   :description lang=en: Tutorial on adding KGOs for testing
   :keywords: KGO, rose stem, development, tutorial
   :property=og:locale: en_GB

.. include:: common.txt

.. _managing-KGOs:

.. highlight:: console

Managing KGOs
=============

Running ANTS on different platforms may result in small numeric differences in
results. Consequently, each site needs to generate a local set of known good
outputs (KGOs) for use in |rose stem| testing.

Initial setup
-------------

Before running the rose stem suite, the environment variable
``ANTS_KGO_DIRECTORY_DEFAULT`` needs to be set to point to a suitable central
location for the :ref:`KGO directory <KGO-directory-structure>` corresponding
to the version of ANTS being installed.  The following steps will populate
this directory with site specific KGO files.  A version specific module file,
site-specific ``ants-launch`` script, or any other appropriate method can be
used for setting the environment variable.

After installing ANTS, and confirming the unittests pass, the rose stem suite
can be used to bootstrap a set of KGO files to protect against future changes.

To do this, run the rose stem suite:

.. versionchanged:: 3.0.0
   The rose stem workflow is now run via ``cylc vip`` rather than ``rose stem``.

.. code-block::

  $ cd <working copy>
  $ cylc vip ./rose-stem -z group=all

The rose stem tasks in the suite will fail, since there are no KGOs yet.  Wait
for the suite to complete, and then run::

  $ cp -r ~/cylc-run/generate_KGOs/runN/share/data/* $ANTS_KGO_DIRECTORY_DEFAULT

At this point, re-running the rose stem suite should result in a passing suite.

This process should be repeated for contrib, with the
``CONTRIB_KGO_DIRECTORY_DEFAULT`` environment variable.

.. _KGO-directory-structure:

KGO directory structure
-----------------------

It is recommended to keep a complete set of KGOs for the current release.  It
may also be necessary to store a set of KGOs for head of trunk, and a number
of previous releases.  The following directory structure is suggested for ANTS
core and contrib::

  ANTS
    ├── developer
    │   ├── contrib
    │   │   └── <full_KGO_files>
    │   └── core
    │       └── <full_KGO_files>
    └── release
        └── X.Y.Z
            ├── contrib
            │   └── <full_KGO_files>
            └── core
                └── <full_KGO_files>

Development changes
-------------------

If a contributor has a change that adds, removes or changes KGOs, then they
should:

1. Add newly generated KGO changes to a local directory.  This only needs to
   be the KGO files needed for any rose stem tests affected by the change,
   rather than the full set of KGOs.
2. Add an ``ANTS_KGO_DIRECTORY_OVERRIDE`` or ``CONTRIB_KGO_DIRECTORY_OVERRIDE``
   variable (that points to the local directory) to the ``[[[environment]]]``
   section of each affected task's runtime entry within the ``flow.cylc``.
3. Seek science owner approval for KGO changes.
4. When the ticket is complete, please include a summary of the KGO changes on
   the ticket template.
