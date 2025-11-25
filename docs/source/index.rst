.. meta::
   :description lang=en: Index and introduction to ANTS user guide
   :keywords: ANTS, index, contribute
   :property=og:locale: en_GB

.. include:: common.txt

.. ANTS documentation master file, created by
   sphinx-quickstart on Fri Mar  4 09:20:25 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

============
Introduction
============

Welcome to the ancillary tools (ANTS) documentation.  ANTS is a Python library
built on top of |Iris| that aims to help you produce ancillary files.

The ANTS library provides routines and tools that will help you when you want
to do any of the following:

1. Produce ancillary files on a new model domain.
2. Produce a new set of ancillaries from new source data.
3. Derive a completely new set of ancillary fields for a new parametrisation scheme.


---------------------
Contributions welcome
---------------------

ANTS development is ongoing as it supports new ancillary science implementations,
new datasets, and new domains. Your assistance in reporting
`bugs <https://code.metoffice.gov.uk/trac/ancil/newticket?component=ants&milestone=Ants%20Support&cc=miao@metoffice.gov.uk>`_
and `documentation <https://code.metoffice.gov.uk/trac/ancil/newticket?component=ants&milestone=Ants%20Support&type=documentation&cc=miao@metoffice.gov.uk>`_
issues is gratefully received.  We're particularly keen to identify where the
documentation could be clearer - suggested improvements are not necessary but
are appreciated.  If you'd prefer not to open a ticket, you can also
:ref:`contact us directly <Contact>`.

=========
Contents:
=========

.. toctree::
   :maxdepth: 2

   introduction.rst
   contributing.rst
   install.rst
   ancillary_generation_pipeline.rst
   tutorials.rst
   core_capabilities.rst
   decomposition.rst
   release_notes/index.rst

.. toctree::
   :maxdepth: 1

   API documentation <lib/modules.rst>
   about.rst
   Accessibility Statement <accessibility.rst>
   Appendix A: F03 Ancillary file time metadata <appendixA_time_handling.rst>
   antslaunch.rst
   glossary.rst

====================
 Indices and tables
====================

* :ref:`genindex`
* :ref:`modindex`
