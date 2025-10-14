#!/bin/bash -l
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
set -eu
echo "Checking for broken links"
cd ${DOCSDIR}
make linkcheck
