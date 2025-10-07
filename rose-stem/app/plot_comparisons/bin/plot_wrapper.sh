#!/bin/bash -l
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.

# Convenience script for automated generation of plots when used in ANTS-related rose-stem suites where
# KGO checks are carried out under the rose_bunch application.
#
# Script assumes a convention where bunch item names are the same as the files being checked.
#
# Usage: plot_wrapper.sh <path_to_rose_bunch_task_work_dir>
#
set -eu

BUNCH_TASK_WORK_DIR=$1 # expected directory for rose_bunch task to generate plots from

echo "[INFO] Analysing rose bunch database at: $BUNCH_TASK_WORK_DIR"

# Directory to store output plots to
PLOT_OUTPUT_FILEPATH=$"$CYLC_WORKFLOW_SHARE_DIR"/plot_comparisons

# Grab a list of task names for .nc files that did not pass - Assumes task names are the same as filenames
NETCDF_COMPARISON_LIST=$(sqlite3 ${BUNCH_TASK_WORK_DIR}/.rose-bunch.db "select name from commands where status is 'fail' and name like '%.nc';")

# Grab the source_dir and target_dir environment variables from the config table
# Because these are strings, the environment variables in them need expanding out, which is what the printf operations do
export SOURCE_DIR=$(sqlite3 ${BUNCH_TASK_WORK_DIR}/.rose-bunch.db "select value from config where key is 'env_source_dir';")
SOURCE_DIR=$(echo $SOURCE_DIR | envsubst)
export TARGET_DIR=$(sqlite3 ${BUNCH_TASK_WORK_DIR}/.rose-bunch.db "select value from config where key is 'env_target_dir';")
TARGET_DIR=$(echo $TARGET_DIR | envsubst)

for FNAME in $NETCDF_COMPARISON_LIST; do
    echo "[INFO] Invoking plot_comparisons.py for: $FNAME"
    echo "[INFO]" would invoke: plot_comparisons.py $SOURCE_DIR/$FNAME $TARGET_DIR/$FNAME "$PLOT_OUTPUT_FILEPATH"
    plot_comparisons.py ${TARGET_DIR}/${FNAME} ${SOURCE_DIR}/${FNAME} ${PLOT_OUTPUT_FILEPATH}
done
