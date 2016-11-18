# job-scheduler

## Description

## Project Architecture

## Dependencies
    
  1) AWS Credentials (AWS_ACCESS_KEY and AWS_SECRET_ACCESS)
  2) Redis as a Broker and Backend for Celery and keep tracking of Container state

## Build job-scheduler
## Run job-scheduler

## API Endpoints

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
