#!/bin/bash

BASE_URL=http://localhost:8080

echo "######### /PING"
curl -s ${BASE_URL}/ping
echo

echo "######## /SCHEDULE without Content-Type application/json"
curl -s -i -X POST --data '{}' ${BASE_URL}/schedule
echo

echo "######## /SCHEDULE without docker_image"
curl -s -i -H 'Content-Type: application/json' -X POST --data '{ "foo":"bar" }' ${BASE_URL}/schedule
echo

echo "######## /SCHEDULE with null docker_image schedule"
curl -s -i -H 'Content-Type: application/json' -X POST --data '{ "docker_image": ""}' $BASE_URL/schedule
echo

echo "######## /SCHEDULE without formated schedule"
curl -s -i -H 'Content-Type: application/json' -X POST --data '{ "docker_image": "alpine:latest", "schedule": "123"}' $BASE_URL/schedule
echo

echo "######## /SCHEDULE with env type dict"
curl -s -i -H 'Content-Type: application/json' -X POST --data '{ "docker_image": "alpine:latest", "schedule": "2016-11-17 23:59:59", "env": {"foo": "bar"}}' $BASE_URL/schedule
echo

echo "######## /SCHEDULE with null cmd"
curl -s -i -H 'Content-Type: application/json' -X POST --data '{ "docker_image": "alpine:latest", "schedule": "2016-11-17 23:59:59", "env": ["key1=value=1", "key2=value2", "key3=value3"], "cmd": "" }' $BASE_URL/schedule
echo

echo "######## /SCHEDULE valid"
curl -s -i -H 'Content-Type: application/json' -X POST --data '{ "docker_image": "alpine:latest", "schedule": "2016-11-17 23:59:59", "env": ["key1=value=1", "key2=value2", "key3=value3"], "cmd": "sleep 30" }' $BASE_URL/schedule
echo
