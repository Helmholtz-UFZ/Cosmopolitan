#!/bin/bash

set -e

source .env

job_id=$1

scp -qr "$CLUSTER_USER@$CLUSTER_MACHINE:$CLUSTER_WORK_DIR/$job_id/"*.npy "$WEB_INPUT_DIR/$job_id/" 
