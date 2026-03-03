.. meta::
   :description lang=en: Tutorial on adding sources for testing
   :keywords: source, sources, rose stem, development, tutorial
   :property=og:locale: en_GB

.. include:: common.txt


Managing Sources
================
ANTS rose stem tests require source data to run. This source data needs to be stored
locally. ANTS will look for the source data using an environment variable.

Initial setup
-------------

Before running the rose stem workflow, the environment variable
``ANTS_SOURCES_DIRECTORY_DEFAULT`` needs to be set to point to a suitable central
location for the :ref:`source directory <source-directory-structure>` corresponding
to the version of ANTS being installed.  A version specific module file,
site-specific ``ants-launch`` script, or any other appropriate method can be
used for setting the environment variable.

.. _source-directory-structure:

Source directory structure
--------------------------

The rose stem tests will assume the source data has the following structure
(using the legacy ``contrib`` name rather than ``ancillary-file-science`` for
consistency with existing installations)::

  ANTS
    ├── developer
    │   ├── contrib
    │   │   └── <App_name>
    │   │       └── <app_source_files>
    │   └── core
    │       └── <App_name>
    │           └── <app_source_files>
    └── release
        └── X.Y.Z
            ├── contrib
            │   └── <App_name>
            │       └── <app_source_files>
            └── core
                └── <App_name>
                    └── <app_source_files>

Development changes
-------------------

If a contributor has a change that adds, removes or changes rose stem source files, then
they should modify the rose-app.conf file of the rose stem app to point to the new or
modified file and include the changes on the ticket template.
