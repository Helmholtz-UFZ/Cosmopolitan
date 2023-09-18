#!/bin/bash

set -e

source .env

job_id=$1
cluster_job_id=$2

status=$(ssh -qT "$CLUSTER_USER"@"$CLUSTER_MACHINE" "sacct -j $cluster_job_id --format=State,JobID --noheader | grep -v '\.batch' | awk '{print \$1}'")
echo "$status"
if [ "$status" == "PENDING" ]; then
    exit 0
fi

ssh -qT "$CLUSTER_USER"@"$CLUSTER_MACHINE" "cat $CLUSTER_WORK_DIR/$job_id/logs"
