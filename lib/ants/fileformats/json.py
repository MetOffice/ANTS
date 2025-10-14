# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import json

import numpy as np


class JSONLoader(object):
    """JSON loader"""

    def __init__(self, keys=None, dtypes=None, case_sensitive=False):
        """
        JSON loader that handles validity checks, case handling.

        Parameters
        ----------
        keys : :obj:`str`, optional
            The key name(s) to read from the JSON.  When not provided, all keys
            are returned from the file.
        dtypes : :obj:`str`, optional
            These dtypes correspond to the return numpy dtype of the values
            extracted from the json.  See :class:`numpy.dtype`.  If not
            provided, values extracted from the json are returned as-is.
        case_sensitive : :obj:`bool`, optional
            Determine whether the keys provided should be a case sensitive
            match with that in the file or not.

        """
        if keys is not None and isinstance(keys, str):
            keys = [keys]
        if dtypes is not None and isinstance(dtypes, str):
            dtypes = [dtypes]
        if dtypes is not None and keys is None:
            raise ValueError("dtypes provided but keys not provided.")
        if dtypes:
            if len(dtypes) != len(keys):
                msg = "dtypes length {} not equal to the provided keys " "length {}"
                raise ValueError(msg.format(len(dtypes), len(keys)))
            dtypes = [np.dtype(dtype) for dtype in dtypes]

        self._case_sensitive = bool(case_sensitive)
        if keys:
            if len(set(keys)) != len(keys):
                msg = "Duplicate keys? {}"
                raise ValueError(msg.format(keys))

            if not self._case_sensitive:
                nkeys = [req.lower() for req in keys]
                if len(keys) != len(set(nkeys)):
                    msg = "Keys: {} appear to be case sensitive".format(keys)
                    raise ValueError(msg)
                keys = nkeys
        self._keys = keys
        self._dtypes = dtypes

    def _check_validity(self, dic):
        keys = dic.keys()
        if not self._case_sensitive:
            keys = [key.lower() for key in keys]

        if self._keys:
            mkeys = set(keys)
            rkeys = set(self._keys)
            diff = rkeys - mkeys
            if diff:
                raise KeyError("Keys: {} missing from file".format(diff))

            # Remove keys we weren't requesting.
            stray_keys = mkeys - rkeys
            [dic.pop(dd) for dd in stray_keys]

        if self._dtypes and self._keys:
            for key, dtype in zip(self._keys, self._dtypes):
                try:
                    len(dic[key])
                    dic[key] = np.array(dic[key], dtype)
                except TypeError:
                    dic[key] = dtype.type(dic[key])

    def load(self, filename):
        """
        Load the provided JSON and return a dictionary.

        Parameters
        ----------
        filename : str
            Filepath for the JSON file.

        Returns
        -------
        : dict
            Dictionary representing the requested keys from the JSON.

        """
        with open(filename, "r") as fh:
            dic = json.load(fh)
        self._check_validity(dic)
        return dic


def load(filename, **kwargs):
    """
    JSON loader

    Parameters
    ----------
    **kwargs :
        See :class:`JSONLoader`

    Returns
    -------
    : dict
        Dictionary representing the requested keys from the JSON.

    """
    jloader = JSONLoader(**kwargs)
    return jloader.load(filename)
