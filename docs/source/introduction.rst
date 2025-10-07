.. meta::
   :description lang=en: An overview of ANTS
   :keywords: documentation, ancillary, process
   :property=og:locale: en_GB

.. include:: common.txt

What is ANTS?
=============

ANTS is a Python library that provides interfaces and routines for carrying out
common operations needed to produce |ancillary files|. It is built on top of |Iris|
and uses |Mule| to write |Unified Model| (UM) ancillary files.

In addition, some standard applications are provided to support:

 * regridding of data
 * filling data
 * merging datasets
 * converting files to ancillary file format
 * generation of |polygon files| that may be needed for ancillary generation

What is ANTS not?
=================

While ANTS provides a library for carrying out common operations needed
for ancillary generation, it is:

 * not where ancillary science routines live
 * not where ancillary generation workflows live
 * not the library for generation of Unstructured Grid ancillaries


Related areas
=============

When carrying out work generating or writing new ancillary generation code, a
number of areas beyond the ANTS library itself will likely be encountered.

.. _Contrib_introduction:

Contrib
-------

Contrib is a central location for the lodging of ANTS based ancillary science
routines. The codes in there are owned by scientists, with technical advice and
assurance provided by the ANTS developers. A |rose stem| workflow exists in
contrib to enable routine testing of the ancillary science routines lodged
there - known as "Apps" - as updates are made to the ANTS library.

.. _Datasets_introduction:

Datasets
--------

In order to generate an ancillary file, you will normally need some input data
which is then passed to an ancillary science routine to produce the required
outputs. Such datasets - commonly refered to as "master files" - may come in a
variety of formats, from a range of different sources, with differing
structures even for the same sort of input domain. As such, some
"pre-processing" will typically be required in order to get the source dataset
in an appropriate state for use by the ancillary science routines it is to be
processed by. It is likely that when using a new dataset you will need to write
a new "pre-processor" for it. You will want to refer to the relevant Contrib
App to understand what is needed and there may be related pre-processors
available that you could use as starting points.

Ideally, files input into ancillary science routines should be in |netCDF| format
as ANTS (and Iris) is well optimised for working with this format. It also has
the added benefit of allowing metadata to be recorded with the data itself -
allowing capture of provenance, licensing, and distribution information.

.. _Workflows_introduction:

Ancillary Workflows
-------------------

Ancillary Workflows are |cylc| based workflows (suites) that are owned,
maintained, and developed by science teams and are not maintained by the ANTS
developers. These workflows will often include one or more jobs running Contrib
Apps to process "Master Files" into ancillary files, and are the typical entry
point for someone wanting to produce a new ancillary file rather than the ANTS
library itself. Examples of these are the Global Atmosphere (GA), Regional
Atmosphere (RA), and |JULES| suites.

The CAP
-------

The CAP was a Fortran based libary previously used to generate Unified Model
ancillary files. It is, however, long since unmaintained and unsupported. Much
work has been put into providing contrib implementation of equivalent, or
newer, science to enable migration away from the CAP to ANTS based contrib
implementations.

UG-ANTS / UG-Contrib
--------------------

With the move to |LFRic|, our models move to using a |cubesphere| grid and it becomes
necessary to have tooling and write new science routines to support the new
grid and model requirements. ANTS does not support generation of the
unstructured grid ancillary files needed for this. Instead, a separate UG-ANTS
and associated UG-Contrib are being developed. Due to the various complexities
both in terms of implementations needed, along with the structure of the
existing ANTS and Contrib codes, an active decision was made to develop these
as distinct, separate things. These libraries follow the same principles as
regular ANTS and Contrib - UG-ANTS is the underpinning Python library, and
UG-Contrib is where ancillary science routines for generating U-Grid ancillary
files live.

Contacting Us
=============

If you want support with ANTS, want to report a bug, or are interested in
contributing new functionality feel free to :ref:`contact us<about>`.
