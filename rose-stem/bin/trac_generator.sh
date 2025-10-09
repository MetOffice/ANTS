#!/usr/bin/env bash
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
set -eu

# CYLC8 compatible suite log dumping script for trac template completion.

export DB_LOCATION=${CYLC_WORKFLOW_RUN_DIR}/log/db
export OUTPUT_STATUS_LOG=${CYLC_WORKFLOW_RUN_DIR}/trac_status.log
export OUTPUT_DURATION_LOG=${CYLC_WORKFLOW_RUN_DIR}/trac_durations.log

# Suppress ants-launch debug logs
export QUIET_MODE=true

# Put ants-launch and durations_main.py on the path
export PATH=${CYLC_WORKFLOW_SHARE_DIR}/fcm_make_ants/build/bin/:$PATH
export PATH=${CYLC_WORKFLOW_SHARE_DIR}/fcm_make_ants/build/utils/generate_logs/:$PATH

# User info for OUTPUT_STATUS_LOG
date > $OUTPUT_STATUS_LOG
echo "-----" >> $OUTPUT_STATUS_LOG
echo $USER ran suite located at: $CYLC_WORKFLOW_RUN_DIR >> $OUTPUT_STATUS_LOG
echo "-----" >> $OUTPUT_STATUS_LOG

# Verson info for OUTPUT_STATUS_LOG
echo "=== Revision information ===" >> $OUTPUT_STATUS_LOG

echo "{{{" >> $OUTPUT_STATUS_LOG
cat ${CYLC_WORKFLOW_RUN_DIR}/log/version/vcs.json >> $OUTPUT_STATUS_LOG
echo -e "\n}}}" >> $OUTPUT_STATUS_LOG

# Generate test status table for OUTPUT_STATUS_LOG
echo "=== Test Results ===" >> $OUTPUT_STATUS_LOG
echo " || '''task''' || '''status''' || " >> $OUTPUT_STATUS_LOG
ants-launch sqlite3 -separator " || " $DB_LOCATION "select '', name, status, '' from task_states" >> $OUTPUT_STATUS_LOG

# Generate OUTPUT_DURATION_LOG
ants-launch durations_main.py $DB_LOCATION $OUTPUT_DURATION_LOG github
