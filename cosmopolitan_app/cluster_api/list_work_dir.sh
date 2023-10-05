#!/bin/bash

set -e

source .env

ssh -qT "$CLUSTER_USER"@"$CLUSTER_MACHINE" "ls $CLUSTER_WORK_DIR"
