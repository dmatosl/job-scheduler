#!/bin/bash
# Author: dmatosl <https://github.com/dmatosl>

set -euf -o pipefail

### APP DEFAULT CONFIG
LOG_LEVEL=${LOG_LEVEL:-"INFO"}
ACCESS_LOGFILE=${ACCESS_LOGFILE:-"-"}

# REDIS CONFIG
REDIS_HOST=${REDIS_HOST:-"redis"}
REDIS_PORT=${REDIS_PORT:-"6379"}

export LOG_LEVEL ACCESS_LOGFILE REDIS_HOST REDIS_PORT

export REDIS_HOST REDIS_PORT

python deploy-job-scheduler.py
