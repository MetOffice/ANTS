# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
#
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
from datetime import datetime

import iris
import numpy as np
import shapely

# Need to add lib directory to sys.path in order to import ants
sys.path.insert(0, os.path.abspath("../../bin"))  # For autodoc
sys.path.insert(0, os.path.abspath("../../lib"))  # For autodoc

# E402: module import not at top of file, but we need the above lines of
# code in order to add ants to sys.path
import ants  # noqa: E402

# -- Project information -----------------------------------------------------

project = "ANTS"
copyright = f"2015 - {datetime.now().year}, Met Office"
author = "Model Inputs and Outputs team, Met Office"

# Avoid using the full version string if it is a developer version
if "dev" in ants.__version__:
    version = "developer"
else:
    version = ants.__version__
release = version

iris_version = iris.__version__
numpy_version = np.__version__.rsplit(".", 1)[0]
shapely_version = shapely.__version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.extlinks",
    "sphinx.ext.viewcode",
    "sphinxarg.ext",
    "sphinx_copybutton",
    "sphinx_sitemap",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

intersphinx_mapping = {
    "python": (
        f"https://docs.python.org/{sys.version_info.major}.{sys.version_info.minor}",
        None,
    ),
    "iris": (f"https://scitools-iris.readthedocs.io/en/v{iris_version}", None),
    "mule": ("https://code.metoffice.gov.uk/doc/um/mule/latest", "mule-objects.inv"),
    "numpy": (f"https://numpy.org/doc/{numpy_version}/", None),
    "shapely": (f"https://shapely.readthedocs.io/en/{shapely_version}/", None),
    "dask": ("https://docs.dask.org/en/stable/", None),
}

extlinks = {
    "anciltrac": ("https://code.metoffice.gov.uk/trac/ancil/%s", "ancil trac %s"),
    "ancilwiki": ("https://code.metoffice.gov.uk/trac/ancil/wiki/%s", "ancil wiki %s"),
    "antsworkingpractices": (
        "https://code.metoffice.gov.uk/trac/ancil/wiki/ANTS/WorkingPractices%s",
        "%s",
    ),
    "contrib": (
        "https://code.metoffice.gov.uk/trac/ancil/browser/contrib/trunk/%s",
        "contrib %s",
    ),
    "fcm": ("http://metomi.github.io/fcm/doc/%s", "fcm %s"),
    "source": (
        "https://code.metoffice.gov.uk/trac/ancil/browser/ants/trunk/%s",
        "source %s",
    ),
    "ticket": ("https://code.metoffice.gov.uk/trac/ancil/ticket/%s", "#%s"),
}

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "special-members": "__init__, __call__",
}

# Make sphinx-copybutton skip all prompt characters in pygments highlighted
# code blocks.
copybutton_exclude = ".linenos, .gp"
# Set default syntax highlighting to python:
highlight_language = "python-console"

# Ignore the following warnings in nitpicky mode
# TODO https://github.com/MetOffice/ANTS/issues/89: Remove the entries relating to
# private classes when we have fixed the documentation tfor these.
nitpick_ignore = [
    ("py:exc", "argparse.ArgumentTypeError"),
    ("py:class", "ants.fileformats.namelist.umgrid._CAPGrid"),
    ("py:class", "ants.regrid.interpolation._StratifyScheme"),
    ("py:class", "ants.regrid.interpolation._StratifyPointsScheme"),
]

# -- Options for HTML output -------------------------------------------------
language = "en"

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "pydata_sphinx_theme"

html_context = {
    "accessibility": "accessibility.rst",
}

# Settings for site map
html_baseurl = "https://metoffice.github.io/ANTS/"
sitemap_locales = [None]
sitemap_url_scheme = "{link}"
html_last_updated_fmt = ""

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

# Link to ANTS Trac page
# Include accessibility in footer
html_theme_options = {
    "github_url": "https://github.com/MetOffice/ANTS",
    "footer_center": [
        "last-updated",
    ],
    "footer_end": [
        "accessibility",
        "theme-version",
    ],
    "show_toc_level": 2,
}

# -- Options for link checking -----------------------------------------------

linkcheck_ignore = [
    r"https://code.metoffice.gov.uk/trac/ancil/newticket.*",
    # Needed due to authentication and redirects on MOSRS breaking linkcheck
    # when linking to specific anchors.  The URLs that need to be matched are
    # currently:
    # https://code.metoffice.gov.uk/doc/um/mule/latest/mule.html#mule.UMFile
    # https://code.metoffice.gov.uk/doc/um/mule/latest/mule.html#mule.Field3
    # https://code.metoffice.gov.uk/doc/um/mule/latest/mule/ancil.html#mule.ancil.AncilFile
    r"https://code.metoffice.gov.uk/doc/um/mule/latest/mule.*\.html\#",
    # Ignore ANTS GitHub while it is private.
    # TODO: Remove from ignore list when repository goes public.
    r"https://github.com/MetOffice/ANTS.*",
]
