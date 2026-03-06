# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
"""
.. deprecated:: 2.2
   This module is deprecated. Filtering functions can now be found in the
   ancillary-file-science repository, under Apps/Orography/orography_filters.py
"""


def raymond(source, epsilon=None, filter_length_scale=None, isotropic=False):
    """
    .. attention::
       The Raymond filter has been removed from the core ants library at version 2.2.
       It has been moved to Apps/Orography/orography_filters.py in the
       ancillary-file-science repository.
       Attempting to use this function will result in an ImportError.
    """
    raise ImportError(
        "The Raymond filter has been removed from the core ants library. It has been"
        " moved to Apps/Orography/orography_filters.py in the ancillary-file-science "
        "repository."
    )
