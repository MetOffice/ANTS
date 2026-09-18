.. meta::
   :description lang=en: Tutorial on managing metadata
   :keywords: metadata, license, licensing, attribution, references, development, tutorial
   :property=og:locale: en_GB

.. include:: common.txt


Managing Metadata
=================

Metadata in this tutorial refers to information about the data in a file, that does not
directly affect that data. For example, licensing information or attributions.

Some ancillary file formats cannot include metadata. Metadata can be very important to
keep alongside the data as often data will have rome form of requirement or restriction
on it. Because of this, ANTS can handle in external metadata files, provided they match
the naming convention of `filename.attribute.accepted-metadata`. The current accepted
metadata attributes are "license", "attribution", "restrictions", "institution",
"acknowledgement", and "references".

This functionality can be turned off through the use of the argument
``--ignore-metadata-files`` on the command line or when calling the ANTS load:

.. code-block:: python

    cube = ants.io.load('data', ignore_metadata_files=True)


.. note::
    Any attributes or files referencing licensing should use the 'license' spelling for
    consistency.

Loading Metadata
----------------

ANTS can load in external metadata files or 'sidecar' files, if they are kept in the
same directory as the data files, and have the same name (including the extension).
Metadata can be loaded alongside all files, including NetCDF files, however ANTS will
not allow you to load a file with a metadata attribute and a sidecar file with the same
attribute. This is to prevent unintentional loss or overwriting of metadata information.

.. note::
    When using wildcards for loading with sidecar files, add the file extension to the
    end to prevent issues with ANTS attempting to load the sidecar files. E.g.
    `data*.pp` rather than `data*`.


Saving Metadata
---------------

Metadata will only be saved to a sidecar file, if the ancil loader is used. This is
because NetCDF files will include the attributes within the file.

The sidecar files produced by ANTS follow the same naming covenstions at those loaded in
`filename.attribute.accepted-metadata`. Only accepted metadata will be written out.
