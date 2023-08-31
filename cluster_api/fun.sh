#!/bin/bash

set -e

load_param() {
    var="$(python3 -c "import sys, json;\
	print(json.load(sys.stdin)['$1'])" \
	< "./parameters_cluster_local.json")"
    echo "$var"
}
