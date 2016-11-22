#!/bin/bash
# Author: dmatosl <https://github.com/dmatols>

set -eof pipefail

### APP DEFAULT CONFIG

# GUNICORN
WORKERS=${WORKERS:-5}
WORKER_CLASS=${WORKER_CLASS:-"sync"} # due to gevent issues with Celery
BIND_ADDR=${BIND_ADDR:-"0.0.0.0:8080"}
LOG_LEVEL=${LOG_LEVEL:-"INFO"}
ACCESS_LOGFILE=${ACCESS_LOGFILE:-"-"}

# REDIS CONFIG
REDIS_HOST=${REDIS_HOST:-"redis"}
REDIS_PORT=${REDIS_PORT:-"6379"}

export WORKERS WORKER_CLASS BIND_ADDR LOG_LEVEL ACCESS_LOGFILE REDIS_HOST REDIS_PORT

# GUNICORN CMD
gunicorn api:app \
 --access-logfile ${ACCESS_LOGFILE} \
 --log-level ${LOG_LEVEL} \
 --bind ${BIND_ADDR} \
 --workers ${WORKERS} \
 --worker-class ${WORKER_CLASS}

