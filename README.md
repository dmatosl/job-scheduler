# job-scheduler

## Description

## Build

## Run

## Examples

POST /schedule
200 OK
```json```
{
    "scheduled_time": "2016-11-12 00:00:00",
    "docker_image": "alpine:latest",
    "docker_env": [
        "foo=bar"
    ]
}

Response
200 OK 
```json```
{
    "id" : "ebacas13poasdA23lk",
    "scheduled_time": "2016-11-12 00:00:00",
    "status": "scheduled"
}

GET /status/ebacas13poasdA23lk
200 OK
```json```
{
    "id": "ebacas13poasdA23lk",
    "scheduled_time": "2016-11-12 00:00:00",
    "status": "running"
}

GET /callback
200 OK
```json```
{
    
}
