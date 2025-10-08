#!/bin/bash -l
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
set -eu

# Set directory level where the nccmp comparison job.err should exist below:
LOG_DIR=$(echo ${CYLC_TASK_LOG_DIR} | sed 's/plot_comparisons/rose_ana/')

# Return the string of filepaths from the job.err:
# -h suppresses returning the job.err path where pattern detected.
# -A2 returns the first two lines after (and including) the detected match.
# Includes sed command to remove the detected pattern (returned to user by default).
FILEPATHS=$(grep -r -h -A2  "RuntimeError: NetCDF comparison failure." ${LOG_DIR} \
| sed 's/RuntimeError: NetCDF comparison failure.//')

# Run two sed commands to isolate the filepaths with detected differences.
TEST_RESULT=$(echo ${FILEPATHS} | sed 's/File1://' | sed 's/ File2.*//')
KGO=$(echo ${FILEPATHS} | sed 's/.*File2://')

# Echo them to be picked up by argparse in plot_comparisons.py
echo ${KGO}
echo ${TEST_RESULT}
