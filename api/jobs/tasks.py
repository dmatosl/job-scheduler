from celery import shared_task
import logging
import json
import time

@shared_task(max_retries=3)
def my_task(a,b):
    return a+b

@shared_task(max_retries=3)
def run_ec2_spot_instance(config):
    logger = logging.getLogger('job_run_ec2_spot_instance')
    logger.debug("running ec2 instance: %s" % config)
    time.sleep(30)
    return jsondumps({
        'spot_id': "zxcasd1123",
        'instance_id': "123kjasdjk",
        'dns_name': "/var/run/docker.sock",
        'ip_address': '127.0.0.1',
        'message': 'success'
    })

@shared_task(max_retries=3)
def run_docker_container(docker_image,env,cmd,ec2_instance):
    logger = logging.getLogger('job_run_docker_container')
    logger.debug("running container: %s, %s, %s, %s" % (docker_image,env,cmd,ec2_instance))
    time.sleep(30)
    return {
        'id': "zxcasd1123",
        'state': "Exited (0)...",
        'status': "exited",
        'instance_id': '123kjasdjk',
        'message': 'success'
    }

@shared_task(max_retries=3)
def terminate_ec2_spot_instance(instance_id):
    logger = logging.getLogger('terminate_ec2_spot_instance')
    logger.debug("terminating intance_id: %s" % (instance_id))
    time.sleep(30)
    return {'message': 'success'}
