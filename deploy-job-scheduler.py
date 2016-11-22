import os
import sys
from config import LOG_FILE, LOG_FORMAT, AWS_SETTINGS
import logging
from api.jobs.utils.aws_spot_instance import AWSSpotInstance
from boto.ec2.connection import EC2Connection
from boto.ec2.connection import EC2ResponseError

# Logging basic
logging.basicConfig(
    filename=LOG_FILE,
    format=LOG_FORMAT,
    level=logging.INFO
)

logger = logging.getLogger('deploy_job_scheduler')

def invalid_credentials():
    print 'Invalid AWS Credentials, please export environment variables AWS_ACCESS_KEY and AWS_SECRET_ACCESS_KEY'
    sys.exit(1)

if not 'AWS_ACCESS_KEY' in os.environ:
    invalid_credentials()

if not 'AWS_SECRET_ACCESS_KEY' in os.environ:
    invalid_credentials()


###### EC2 Security Groups
#logger.info('creating security groups')
#try:
#    cli = EC2Connection(
#        aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
#        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'])

#    job_scheduler_api_sg = cli.create_security_group(
#        'job_scheduler_api_sg',
#        'job_scheduler_api Security Group')

#    job_scheduler_api_sg.authorize('tcp',22,22,'177.68.43.166/32')
#    job_scheduler_api_sg.authorize('tcp',80,80,'0.0.0.0/0')

#    job_scheduler_app_sg = cli.create_security_group(
#        'job_scheduler_app_sg',
#        'job_scheduler_app Security Group')

#    job_scheduler_app_sg.authorize('tcp',2376, 2376, src_group=job_scheduler_api_sg)
#    job_scheduler_app_sg.authorize('tcp',22,22,'177.68.43.166/32')
#    job_scheduler_app_sg.authorize('tcp',2376,2376,'177.68.43.166/32')

#    logger.info('finished creating security groups')
#except Exception as e:
#        logger.info('Failed on security_groups action: %s' % e)


###### EC2 Instance

logger.info("Updating user_data with aws credentials")
user_data = open(os.path.abspath('user_data/user_data_job_scheduler'),'r').read()
user_data = user_data.replace('%AWS_ACCESS_KEY%', os.environ['AWS_ACCESS_KEY'])
user_data = user_data.replace('%AWS_SECRET_ACCESS_KEY%', os.environ['AWS_SECRET_ACCESS_KEY'])

AWS_SETTINGS['AWS_USER_DATA'] = user_data
AWS_SETTINGS['AWS_SECURITY_GROUPS'] = ['default']
#AWS_SETTINGS['AWS_SECURITY_GROUPS'] = ['job_scheduler_app_sg']

logger.info("start ec2 spot instance request")
aws = AWSSpotInstance(AWS_SETTINGS)
state = aws.create_spot_instance()

print "##########################################"
print ""
print "AWS Information"
print ""
print "Instance_id: %s" % aws.instance_id
print "Instance_State: %s" % aws.state
print "Instance_dns_name: %s" % aws.dns_name
print "Instance_ip_address: %s" % aws.ip_address
print ""
print ""
print "SSH Access to Instance: ssh -i <your_key> core@%s" % aws.ip_address
print ""
print "################################# Testing API"
print ""
print "Check if containers job-scheduler-api, job-scheduler-worker and job-scheduler-redis are running (they could take a few seconds to start)"
print ""
print "API Endpoint Healthcheck: http://localhost/healthcheck" % aws.dns_name
print "API Endpoint Schedule: http://localhost/schedule" % aws.dns_name
print "API Endpoint Status: http://localhost/status/<string:id>" % aws.dns_name
print "API Endpoint List: http://localhost/list" % aws.dns_name
print "API Endpoint Callback: http:/localhost/callback" % aws.dns_name
print "##########################################"
