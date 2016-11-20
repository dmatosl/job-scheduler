import os
import sys
import yaml
from config import *
from api.jobs.utils.aws_spot_instance import AWSSpotInstance

def invalid_credentials():
    print 'Invalid AWS Credentials, please export environment variables AWS_ACCESS_KEY and AWS_SECRET_ACCESS_KEY'
    sys.exit(1)

if not 'AWS_ACCESS_KEY' in os.environ:
    invalid_credentials()

if not 'AWS_SECRET_ACCESS_KEY' in os.environ:
    invalid_credentials()

# UPDATE Credentials on user_data_job_scheduler
user_data = yaml.load(open('./user_data_job_scheduler', 'r').read())
user_data['write-files'][0]['content'] = 'TAG="0.0.1"\nAWS_ACCESS_KEY="%s"\nAWS_SECRET_ACCESS_KEY="%s"\n' % (os.environ['AWS_ACCESS_KEY'], os.environ['AWS_SECRET_ACCESS_KEY'])

AWS_SETTINGS['AWS_USER_DATA'] = yaml.dump(user_data)

aws = AWSSpotInstance(AWS_SETTINGS)
state = aws.create_spot_instance()

print "##########################################"
print "Instance_id: %s" % aws.instance_id
print "Instance_State: %s" % aws.state
print "Instance_dns_name: %s" % aws.dns_name
print "Instance_ip_address: %s" % aws.ip_address

print "API Endpoint Healthcheck: http://%s/healthcheck"
print "API Endpoint Schedule: http://%s/schedule"
print "API Endpoint Status: http://%s/status/<string:id>"
print "API Endpoint List: http://%s/list"
print "API Endpoint Callback: http://%s/callback"
print "##########################################"
