import os

# Logging
LOG_FORMAT = '%(asctime)s %(threadName)s %(name)s %(levelname)s %(message)s'
LOG_FILE = "/dev/stdout"
DEBUG = False

# App JSON configs (send http status on json body and jsonschema validation)
JSON_ADD_STATUS = True
JSONSCHEMA_DIR  = os.path.abspath("schemas")

# Redis config
REDIS_HOST = os.environ['REDIS_HOST']
REDIS_PORT = os.environ['REDIS_PORT']
REDIS_DB = "0"
REDIS_MAX_CONNECTIONS = 100
REDIS_PASS = None

# Celery config
CELERY_BACKEND  = "redis://%s:%s" % (REDIS_HOST, REDIS_PORT)
CELERY_BROKER_URL  = "redis://%s:%s" % (REDIS_HOST, REDIS_PORT)
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT=['json']
CELERY_TASK_RESULT_EXPIRES = 18000  # 5 hours.
CELERYBEAT_SCHEDULE = {
    "runs-jobs-mon-each-10-seconds": {
        "task": "api.jobs.tasks.run_jobs_mon",
        "schedule": 30.0,
    },
}

# AWS Configuration
AWS_SETTINGS = {
    "AWS_SECRET_ACCESS_KEY": os.environ['AWS_SECRET_ACCESS_KEY'],
    "AWS_ACCESS_KEY" : os.environ['AWS_ACCESS_KEY'],
    "AWS_AMI" : "ami-4d795c5a",
    "AWS_REGION" : "us-east-1",
    "AWS_PRICE" : "0.1",
    "AWS_INSTANCE_TYPE" : "c3.large",
    "AWS_INSTANCE_COUNT" : "1"
}
