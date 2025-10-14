#!/bin/bash -l
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
set -eu
echo "Building the documentation"
cd ${DOCSDIR}
make clean
make clean-apidoc
make apidoc
make html
echo "Documentation built. "
echo "Run 'gio open ${DOCSDIR}/build/html/index.html' to view"
