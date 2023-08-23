#!/bin/bash

set -e

. ./cluster_api/fun.sh

user=$(load_param "user")
machine=$(load_param "machine")

ssh "$user"@"$machine" "ls"
