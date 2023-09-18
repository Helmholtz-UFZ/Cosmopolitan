#!/bin/bash

set -e

source .env

job_ids=$@

ssh -qT "$CLUSTER_USER"@"$CLUSTER_MACHINE" "cd $CLUSTER_WORK_DIR && rm -r $job_ids"
