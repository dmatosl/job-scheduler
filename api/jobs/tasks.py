from celery import shared_task, task
from celery.utils.log import get_task_logger
from utils.job_store import JobStore
from utils.container import DockerContainer
from utils.aws_spot_instance import AWSSpotInstance
import requests
import json
import time
import re

celery_logger = get_task_logger(__name__)

@shared_task(max_retries=3)
def my_task(a,b):
    return a+b

@shared_task(bind=True, max_retries=3)
def run_ec2_spot_instance(self, job_id, config):
    celery_logger.info("running ec2 instance: %s" % config)
    time.sleep(10)
    return {
        'spot_id': "zxcasd1123",
        'instance_id': "123kjasdjk",
        'instance_state': 'running',
        'dns_name': "192.168.1.193",
        'ip_address': '192.168.1.193',
        'message': 'success'
    }

@shared_task(max_retries=3)
def run_docker_container(ec2_instance, job_id, docker_image, env, cmd):
    celery_logger.info("running container")

    docker = DockerContainer(ec2_instance['dns_name'])
    container_status = docker.run_container(docker_image, env, cmd)

    jobStore = JobStore()
    job_status = jobStore.getJobStatus(job_id)
    job_status['status'] = container_status['State']
    job_status['docker']['container_id'] = container_status['Id']
    job_status['docker']['container_status'] = container_status['State']
    job_status['aws']['spot_id'] = ec2_instance['spot_id']
    job_status['aws']['instance_id'] = ec2_instance['instance_id']
    job_status['aws']['dns_name'] = ec2_instance['dns_name']
    job_status['aws']['ip_address'] = ec2_instance['ip_address']

    jobStore.setJobStatus(job_id, job_status)

    return job_status

@shared_task(max_retries=3)
def run_mon(container, job_id):
    celery_logger.info("starting container mon: %s" % (container) )
    docker = DockerContainer(container['aws']['dns_name'])
    for e in docker.get_docker_instance().events(filters={'id': container['docker']['container_id']},decode=True):
        celery_logger.info("docker event appeared: %s" % e )
        if 'status' in e:
            if e['status'] == 'die':
                celery_logger.info("docker event 'die': %s" % e )
                container['docker']['container_status'] = e['status']
                container['docker']['container_exit_code'] = e['Actor']['Attributes']['exitCode']
                container['status'] = 'finished'

                jobStore = JobStore()
                jobStore.setJobStatus(job_id, container)

                # trigger callback url
                return container

@task()
def run_jobs_mon():
    time.sleep(15)
    return 1+1

@shared_task(max_retries=3)
def terminate_ec2_spot_instance(instance_id,aws_settings):
    celery_logger.info("terminating instance_id: %s" % (instance_id))
    aws = AWSSpotInstance(aws_settings)
    return aws.terminate_spot_instance(instance_id)

@shared_task(bind=True ,max_retries=3)
def run_container(self, job_id, aws_settings, docker_settings):
    checking_attemps = 100
    checking_interval = 3
    try:
        # Create EC2 Image
        jobStore = JobStore()
        aws = AWSSpotInstance(aws_settings)
        aws.create_spot_instance()

        for a in xrange(checking_attemps):
            job = getJobStatus(job_id)
            if job['aws']['ready']:
                break
            time.sleep(checking_interval)

        # RUN Docker Container
        celery_logger.info("ready to run container")
        docker = DockerContainer(aws.dns_name)
        container_status = docker.run_container(docker_image, env, cmd)

        job_status = jobStore.getJobStatus(job_id)
        job_status['status'] = container_status['State']
        job_status['docker']['container_id'] = container_status['Id']
        job_status['docker']['container_status'] = container_status['State']
        job_status['aws']['instance_id'] = aws.instance_id
        job_status['aws']['dns_name'] =  aws.dns_name
        job_status['aws']['ip_address'] = aws.ip_address
        job_status['aws']['state'] = aws.state

        jobStore.setJobStatus(job_id, job_status)

        # Start Docker Container mon
        celery_logger.info("starting container mon: %s" % (job_status['docker']['container_id']) )
        # Waiting for container die state
        for e in docker.get_docker_instance().events(filters={'id': job_status['docker']['container_id']},decode=True):
            celery_logger.info("docker event appeared: %s" % e )
            if 'status' in e:
                if e['status'] == 'die':
                    celery_logger.info("docker event 'die' reached: %s" % e )
                    job_status['docker']['container_status'] = e['status']
                    job_status['docker']['container_exit_code'] = e['Actor']['Attributes']['exitCode']
                    job_status['status'] = 'finished'

                    jobStore.setJobStatus(job_id, container)

                    # trigger callback url
                    req = requests.get("http://169.254.169.254/latest/meta-data/public-hostname")
                    payload={'action': 'terminate', 'instance_id': aws.instance_id}
                    post = requests.post("http://%s/callback" % req.text, json=payload)
                    return job_status

    except Exception as e:
        celery_logger.info('Task execution Failed : %s' % e)
        self.retry(exc=e, countdown=2 ** self.request.retries)
