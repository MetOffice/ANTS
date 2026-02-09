# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import abc
import os
import re
import unittest
from pathlib import Path

import ants

LICENSE_TEMPLATE = """# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details."""


class Common(metaclass=abc.ABCMeta):
    def setUp(self):
        # Only checks the directory from which ants was imported.
        ants_path = Path(ants.__file__).resolve(strict=True)
        working_directory = str(ants_path.parents)
        print("working dir: ", ants_path.parent)
        self.all_filepaths = [
            os.path.join(dirpath, filename)
            for dirpath, _, filenames in os.walk(working_directory[2])
            for filename in filenames
        ]
        print("filepaths: ", self.all_filepaths)
        self._exclude = [
            os.path.join("tests", "resources"),
            os.path.join("tests", "results"),
            ".*.pyc$",
        ]
        # Determine the files in the 'ants' package that do not contain
        # any items in the 'exclude' list:
        self._include_files = [
            filepath
            for filepath in self.all_filepaths
            if not self._string_matches_pattern(filepath, self._exclude)
        ]

    @abc.abstractmethod
    def get_files(self):
        pass

    @staticmethod
    def _string_matches_pattern(string, patterns):
        # Return whether the string matches any pattern in the patterns
        # list.
        result = False
        for pattern in patterns:
            if re.search(pattern, string):
                result = True
                break
        return result

    def _get_files(self, include_list):
        """
        Return all files within the ``ants`` package that match a
        pattern in the include list.

        Parameters
        ----------
        include_list : list
            The regexp patterns to use to filter the files.

        Returns
        -------
        : list
            All files within the ``ants`` package that match a pattern
            in the include list.
        """
        output = [
            filepath
            for filepath in self._include_files
            if self._string_matches_pattern(filepath, include_list)
        ]
        return output


class TestLicenseHeaders(Common, unittest.TestCase):
    def get_files(self):
        """
        Return list of names of python files.

        Python files are defined by a '.py' suffix.

        Returns
        -------
        : list of str
        List of filenames for python files.
        """
        return self._get_files(include_list=[r".*\.py$", r".*\.sh$"])

    @staticmethod
    def check_license_header(filename):
        """Check license header and add where missing."""
        with open(filename, "r") as fh:
            contents = fh.read()
        license_re = re.compile(r"((\#\!.*|\/\*)\n)?" + re.escape(LICENSE_TEMPLATE))
        match = re.match(license_re, contents)
        messages = []
        if not match:
            if re.search("copyright", contents, flags=re.IGNORECASE):
                message = f"{filename}: Corrupted copyright/license notice."
            else:
                message = f"{filename}: Missing copyright/license notice."
            messages.append(message)

        return messages

    def test_license_headers(self):
        files = self.get_files()
        print("files: ", files)
        messages = []
        for fnme in files:
            messages.extend(self.check_license_header(fnme))
        msg = "There were license header failures."
        msg = "{}\n{}".format(msg, "\n".join(messages))
        self.assertFalse(messages, msg)
