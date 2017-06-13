# job-scheduler


## Description
Job-Scheduler is a Backend API for scheduling Jobs (docker containers) execution on fresh AWS EC2 Spot Instances

## Project Architecture
Project is divided in two main components: (API and Worker) both components use Redis as a backend (Persistent data store) and Broker (message queue):

- API - Is a simple python (Flask) [http://flask.pocoo.org/] Restful Json API responsible for parsing requests and enqueuing jobs to Celery Workers perform the job execution. The API implements the following routes:

    * /schedule   : Schedules the job to be executed at the specified date (respecting ISO8601 format) on Celery Broker (async) and returns job status and id
    * /list       : Get all Scheduled jobs and their status  
    * /status/<string:id> : Get a specific job details (id, status, scheduled time, aws\_instance information, docker container information, celery information)
    * /callback   : Receives notification of ready ec2 spot instances to run the desired job and to start instance termination (after job execution)
    * /healthcheck: Simply return live string to check if the service is Up and running

- WORKER - Is a celery instance that executes scheduled jobs base on ISO8601 date. All the jobs are published in a Redis Broker by the API. Once the worker start running the job it will be responsible to keep tracking of the EC2 spot Instance status monitoring and Docker Container status execution. Based on the response it will mark the job as failed, or successfully finished.

## Dependencies

- AWS Credentials (AWS_ACCESS_KEY and AWS_SECRET_ACCESS) for spinning new EC2 spot Instances
- Docker environment (docker-machine, docker for mac,  docker for windows, ...) for building locally and deploying to AWS

## Build job-scheduler

After cloning repository, cwd into src directory and RUN:

    docker build -t job-scheduler:0.0.1 .

## Deploy job-scheduler to EC2

    Add your SSH public key to user_data files (ssh_authorized_keys section):
        job-scheduler/user_data/user_data_docker
        job-scheduler/user_data/user_data_job_scheduler

    export AWS_ACCESS_KEY=yourAccessKey
    export AWS_SECRET_ACCESS_KEY=yourSecretAccessKey

    docker run --rm -it \
      -e "AWS_ACCESS_KEY=${AWS_ACCESS_KEY}" \
      -e "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}" \
      job-scheduler:0.0.1 \
      /bin/bash deploy.sh

It will output the EC2 Instance information

These commands will spinnup an EC2 CoreOS instance and deploy 3 Containers:

- job-scheduler-redis (backend and broker)
- job-scheduler-worker (celery worker for job execution)
- job-scheduler-api (Restful Json API)

## API Endpoints
These API is not open to public internet by default, so it is necessary to access the API locally (ssh to the ec2 instance to perform the tests).
It is recommended to setup Security Groups and limit API access (these topic is not covered on this project).
Examples on how to create security groups were added to file deploy-job-scheduler.py

### POST /schedule

Required Header: 'Content-Type: application/json'

```json
{
  "schedule": "2016-11-22T19:39:22Z",
  "docker_image": "alpine:latest",
  "env": [
      "key=value",
      "key1=value=1"
  ],
  "cmd": "sleep 60"
}
```

Parameters:

- schedule: ISO8601 date (Required)
- docker_image: any valid docker image from public or private registry (Required)
- env: list of "key=value" pairs (not required by default)
- cmd: command to be executed (not required by default)

  ***NOTE for private docker registry: you will need to add --insecure-registry myprivateregistry.com:XXXX flag to user_data/user_data_docker Docker Service definition***

Curl Example:

```bash
    # scheduling job for within 6 minutes
    # current data + 6 minutes
    run_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ" -d '+6 minutes')

    curl -s -i -H 'Content-Type: application/json' \
      -X POST --data "{ \"docker_image\": \"python:2.7-slim\", \"schedule\": \"${run_date}\", \"env\": [\"key1=value\", \"key2=value2\"] }" \
       localhost/schedule
```

Response

Content-Type: application/json

200 OK

```json
{
  "status": "scheduled",
  "message": "job successfully scheduled",
  "id": "xqKQiunYlaKrPhDSfj06tUzSvPiGJJ9G"
}
```

### GET /status/xqKQiunYlaKrPhDSfj06tUzSvPiGJJ9G

Content-Type: application/json

200 OK
```json
{
  "status": "running",
  "schedule": "2016-11-18T23:59:59",
  "aws": {
    "instance_id": "i-0bfe22184ff4c092c",
    "dns_name": "ec2-107-23-178-40.compute-1.amazonaws.com",
    "ready": true,
    "ip_address": "107.23.178.40",
    "state": "running"
  },
  "celery": {
    "job_parent_id": "1d594747-a0c7-4b54-a33b-c6098fbefc38"
  },
  "docker": {
    "container_id": "4ac3b8eb8b32006160be15c34e87132f545f593ec066721f6bb1582a04f6765a",
    "container_status": "running",
    "environment": [
      "key1=value",
      "key2=value2"
    ],
    "command": "sleep 120",
    "docker_image": "alpine:latest",
    "container_exit_code": ""
  },
  "id": "xqKQiunYlaKrPhDSfj06tUzSvPiGJJ9G"
}
```

### GET /list

Content-Type: application/json

200 OK
```json
{
  "jobs": [
    {
      "status": "scheduled",
      "id": "vmi6xFA22PX4FDTWSEQlNl2RKS5Wyz8E",
      "schedule": "2016-11-22T20:10:40Z"
    },
    {
      "status": "failed",
      "id": "ocFCwTHM20wOtIuLC0hCaUJTCxi20TQS",
      "schedule": "2016-11-22T20:09:40Z"
    },
    {
      "status": "running",
      "id": "Ag0L7XG978UD75CX5xHcZ5tokmYFWNPL",
      "schedule": "2016-11-22T20:08:40Z"
    },
    {
      "status": "finished",
      "id": "xqKQiunYlaKrPhDSfj06tUzSvPiGJJ9G",
      "schedule": "2016-11-18T23:59:59"
    }
  ]
}
```

### POST /callback

Terminate instance

```json
{
  "action": "terminate",
  "job_id": "xqKQiunYlaKrPhDSfj06tUzSvPiGJJ9G",
  "instance_id": "i-0bfe22184ff4c092c"
}
```

Parameters:

- action: 'terminate' or 'update': used to trigger instance termination or update instance status (ready: true)
- job_id: auto filled by the ec2 instance that run the job
- instance_id: auto filled by the ec2 instance that run the job (Required)

Mark ec2 instance as ready for job execution

```json
{
  "action": "update",
  "job_id": "xqKQiunYlaKrPhDSfj06tUzSvPiGJJ9G",
  "instance_id": "i-0bfe22184ff4c092c"
}
```


# Reference doc/guides:
http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html
https://gist.github.com/jakedahn/374e2e54fdcef711bf2a
https://coreos.com/os/docs/latest/customizing-docker.html
http://flask.pocoo.org/docs/0.11/patterns/celery/
http://docs.celeryproject.org/en/latest/userguide/canvas.html#guide-canvas
http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
