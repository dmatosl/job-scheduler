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

@shared_task(bind=True, max_retries=3)
def terminate_ec2_spot_instance(self, instance_id, aws_settings):
    try:
        celery_logger.info("terminating instance_id: %s" % instance_id)
        aws = AWSSpotInstance(aws_settings)
        return aws.terminate_spot_instance(instance_id)
    except Exception as e:
        celery_logger.info('terminate_ec2_spot_instance Task execution Failed : %s' % e)
        self.retry(exc=e, countdown=2 ** self.request.retries)


@shared_task(bind=True ,max_retries=3)
def run_container(self, job_id, aws_settings, docker_settings):
    checking_attemps = 100
    checking_interval = 5
    try:

        jobStore = JobStore()

        # Get callback url
        callback_url = jobStore.getJobNotificationUrl()

        job_status = jobStore.getJobStatus(job_id)

        # Check if instance was created (retries)
        if len(job_status['aws']['instance_id']) > 1:
            celery_logger.info("instance already exists, trying to reuse (%s)" % job_status['aws']['instance_id'])
            aws = AWSSpotInstance(aws_settings)
            aws.update_instance(job_status['aws']['instance_id'])
        else:
            # Update user_data for new instance
            user_data = aws_settings['AWS_USER_DATA'].replace('%JOB_ID%', job_id)
            user_data = user_data.replace('%JOB_SCHEDULER_API_CALLBACK_URL%',callback_url)
            aws_settings['AWS_USER_DATA'] = user_data

            # Create EC2 Instance
            aws = AWSSpotInstance(aws_settings)
            state = aws.create_spot_instance()
            celery_logger.info("aws instance created (%s)" % aws.instance_id)

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
            if a == (checking_attemps -2) :
                raise Exception('ec2 instance  did not became ready on time')

            time.sleep(checking_interval)

        # RUN Docker Container
        celery_logger.info("ready to run container %s" % job_id)
        docker = DockerContainer(aws.dns_name)
        container_status = docker.run_container(
            docker_settings['docker_image'],
            docker_settings['env'],
            docker_settings['cmd']
        )

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
