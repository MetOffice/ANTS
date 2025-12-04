# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
import unittest.mock as mock

import ants.tests
from ants.decomposition import MultiprocessingDomainDecompose


class Test__run_num_processes(ants.tests.TestCase):
    def setUp(self):
        patch = mock.patch("ants.decomposition.dask.config.set")
        self.patched_dset = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("ants.decomposition.db.from_sequence")
        self.patched_dseq = patch.start()
        self.addCleanup(patch.stop)

        self.args = [[mock.sentinel.iterable]]

    def test_environmental_variable_hook(self):
        # Number of processes defined in an environmental variable.
        env = {"ANTS_NPROCESSES": "10"}
        patch = mock.patch(
            "ants.decomposition.os.getenv", side_effect=lambda x, y: env.get(x, y)
        )
        with patch:
            decomp = MultiprocessingDomainDecompose()
            decomp._run(mock.sentinel.operation, self.args)
        self.patched_dset.assert_called_once_with(
            {"multiprocessing.context": "fork"}, num_workers=9
        )
