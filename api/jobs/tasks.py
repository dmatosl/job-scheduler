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

@shared_task(bind=True, max_retries=3)
def terminate_ec2_spot_instance(self, instance_id, aws_settings):
    try:
        celery_logger.info("terminating instance_id: %s" % (instance_id))
        aws = AWSSpotInstance(aws_settings)
        return aws.terminate_spot_instance(instance_id)
    except Exception as e:
        celery_logger.info('terminate_ec2_spot_instance Task execution Failed : %s' % e)
        self.retry(exc=e, countdown=2 ** self.request.retries)


@shared_task(bind=True ,max_retries=3)
def run_container(self, job_id, aws_settings, docker_settings):
    checking_attemps = 100
    checking_interval = 3
    try:

        jobStore = JobStore()

        # Get callback url
        callback_url = jobStore.getJobNotificationUrl()

        job_status = jobStore.getJobStatus(job_id)

        # Check if instance was created (retries)
        if len(job_status['aws']['instance_id']) > 1:
            celery_logger("instance already exists, trying to reuse (%s)" % job_status['aws']['instance_id'])
            aws = AWSSpotInstance(aws_settings)
            aws.update_instance(job_status['aws']['instance_id'])
        else:
            # Update user_data for new instance
            user_data = aws_settings['AWS_USER_DATA'].replace('%JOB_ID%', job_id)
            user_data = aws_settings['AWS_USER_DATA'].replace('%JOB_SCHEDULER_API_CALLBACK_URL%',callback_url)
            aws_settings['AWS_USER_DATA'] = user_data

            # Create EC2 Instance
            aws = AWSSpotInstance(aws_settings)
            state = aws.create_spot_instance()
            celery_logger.info("aws instance created (%s, %s, %s, %s)" % aws.instance_id, aws.dns_name, aws.ip_address, aws.state )

        job_status['aws']['instance_id'] = aws.instance_id
        job_status['aws']['dns_name'] =  aws.dns_name
        job_status['aws']['ip_address'] = aws.ip_address
        job_status['aws']['state'] = aws.state

        # update ec2 instance -> jobStore
        celery_logger.info('updating ec2 instance information')
        jobStore.setJobStatus(job_id, job_status)

        for a in xrange(checking_attemps):
            job_status = jobStore.getJobStatus(job_id)
            celery_logger.info("checking if aws instance is ready (%s)" % job_status['aws']['ready'])
            if job_status['aws']['ready'] == True:
                break
            time.sleep(checking_interval)

        # RUN Docker Container
        celery_logger.info("ready to run container %s" % job_id)
        docker = DockerContainer(aws.dns_name)
        container_status = docker.run_container(docker_image, env, cmd)

        job_status['status'] = container_status['State']
        job_status['docker']['container_id'] = container_status['Id']
        job_status['docker']['container_status'] = container_status['State']

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
                    payload = {'action': 'terminate', 'instance_id': aws.instance_id, 'job_id': job_id}
                    post = requests.post(callback_url, json=payload)
                    return job_status

    except Exception as e:
        celery_logger.info('Task execution Failed : %s' % e)
        self.retry(exc=e, countdown=2 ** self.request.retries)
