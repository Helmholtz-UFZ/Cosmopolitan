#!/bin/bash

set -e

source .env

job_id=$1

scp -qr "$WEB_INPUT_DIR/$job_id" "$CLUSTER_USER@$CLUSTER_MACHINE:$CLUSTER_WORK_DIR"

ssh -qT "$CLUSTER_USER"@"$CLUSTER_MACHINE" "./start_job_cluster.sh $job_id $CLUSTER_WORK_DIR $CLUSTER_PYTHON_ENV_PATH $CLUSTER_REPO_DIR"
