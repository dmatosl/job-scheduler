# job-scheduler

## Description

## Project Architecture

## Dependencies

- AWS Credentials (AWS_ACCESS_KEY and AWS_SECRET_ACCESS)
- Redis as a Broker and Backend for Celery and keep tracking of Container/EC2 Instance state

## Build job-scheduler

After cloning repository, cwd into src directory and RUN:

    docker build -t job-scheduler:0.0.1 .

## Deploy job-scheduler to EC2

    export AWS_ACCESS_KEY=yourAccessKey
    export AWS_SECRET_ACCESS_KEY=yourSecretAccessKey

    docker run --rm -it \
      -e "AWS_ACCESS_KEY=${AWS_ACCESS_KEY}" \
      -e "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}" \
      job-scheduler:0.0.1 \
      /bin/bash deploy.sh

These commands will spinup an EC2 CoreOS instance and deploy 3 Containers:

- job-scheduler-redis
- job-scheduler-worker
- job-scheduler-api


## API Endpoints
These API is not open to public internet by default. It is recommended to setup Security Groups and limit API access (these topic is not covered on this project)

POST /schedule
200 OK
```json```
{
    "schedule": "2016-11-12 00:00:00",
    "docker_image": "alpine:latest",
    "docker_env": [
        "foo=bar"
    ],
    "cmd": "sleep 60"
}
```

Response
200 OK
```json```
{
    "id" : "7aab581b-39c6-410d-a6a5-5db60ba4c9da",
    "message": "scheduled"
}
```

GET /status/7aab581b-39c6-410d-a6a5-5db60ba4c9da
200 OK
```json```
{
    "id": "ebacas13poasdA23lk",
    "scheduled_time": "2016-11-12 00:00:00",
    "status": "running"
}
```

GET /callback
200 OK
```json```
{

}
```

# Reference doc/guides:
http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html
https://gist.github.com/jakedahn/374e2e54fdcef711bf2a
https://coreos.com/os/docs/latest/customizing-docker.html
http://flask.pocoo.org/docs/0.11/patterns/celery/
http://docs.celeryproject.org/en/latest/userguide/canvas.html#guide-canvas
http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
