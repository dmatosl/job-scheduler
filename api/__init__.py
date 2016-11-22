from flask import Flask, make_response, jsonify, request
from flask_restful import Api, Resource, reqparse, abort
from celery import Celery
from celery.result import AsyncResult
from celery.task.control import inspect
from celery import chain
from jobs.tasks import *
from jobs.utils.job_store import JobStore
from jobs.utils.id_generator import id_generator
import dateutil.parser
import iso8601
from iso8601 import ParseError
import logging
import time
import requests
from requests.exceptions import Timeout, ConnectTimeout, ConnectionError

# Start Flask APP
app = Flask(__name__)
app.config.from_object('config')
api = Api(app)

# Logging basic
logging.basicConfig(
    filename=app.config['LOG_FILE'],
    format=app.config['LOG_FORMAT'],
    level=logging.DEBUG
)

# Define Callback url
try:
    req = requests.get("http://169.254.169.254/latest/meta-data/public-hostname", timeout=3.0)
    callback_url = "http://%s/callback" % req.text
except (Timeout, ConnectTimeout) as e:
    callback_url = 'http://127.0.0.1/callback'

conf = JobStore()
conf.setJobNotificationUrl(callback_url)

# Celery configuration
celery = Celery("jobs", broker=app.config['CELERY_BROKER_URL'],
                    backend=app.config['CELERY_BACKEND'])
celery.conf.update(app.config)
#celery.autodiscover_tasks(['jobs'])

# Schedule Parser
schedule_parser = reqparse.RequestParser()
schedule_parser.add_argument('docker_image',type=str, required=True, location='json')
schedule_parser.add_argument('schedule',type=str, required=True, location='json')
schedule_parser.add_argument('cmd',type=str, required=False, location='json')

# Callback Parser
callback_parser = reqparse.RequestParser()
callback_parser.add_argument('action',type=str, required=True, location='json')
callback_parser.add_argument('instance_id',type=str, required=True, location='json')
callback_parser.add_argument('job_id', type=str, required=True, location='json')

class Healthcheck(Resource):
    def get(self):
        return {'message': 'live'}

class Schedule(Resource):

    def post(self):
        """
        Action: POST
        Uri: /schedule
        Payload:
         Content-Type: application/json
         {
            "docker_image": "alpine:latest",
            "schedule": "2016-11-17 02:00:01",
            "env": ["key=value", "key2=value2"],
            "cmd": "sleep 30"
         }

        Description: Parse Request Body (json) and schedule job
        on Celery
        """
        logger = logging.getLogger("Schedule")
        data = request.get_json()
        jobStore = JobStore()

        # Validate Json Schema with required args (docker_image, schedule)
        args = schedule_parser.parse_args()

        # Validate docker_image content
        if len(args['docker_image']) == 0:
            logger.debug("docker_image is null")
            return {'message': {'docker_image': 'can not be null'}}, 400

        # Validate docker cmd
        if not args['cmd'] == None:
            logger.debug("cmd: %s" % args)
            if len(args['cmd']) == 0:
                logger.debug("docker cmd is null")
                return {'message': {'cmd': 'can not be null'}}, 400
        else:
            data['cmd'] = ''

        # Validate date format
        try:
            valid_date = iso8601.parse_date(args['schedule'])
        except (KeyError, TypeError, ValueError, ParseError) as e:
            logger.debug("Date format validation Exception: %s" % e)
            return {'message': {'schedule': 'schedule does not match ISO-8601 date format'}}, 400

        # Validate env type
        if 'env' in data:
            if type(data['env']) != type([]) :
                logger.debug("Env validation is not a list: (type: %s, data: %s)" % (type(data['env']), data) )
                return {'message': {'env': 'must be a list'}}, 400
        else:
            data['env'] = ''

        docker_job_settings = {
            'docker_image': args['docker_image'],
            'env': data['env'],
            'cmd': data['cmd']
        }

        # generate_uuid
        uuid = id_generator()

        logger.info("preparing docker container settings: %s" % docker_job_settings)

        # Schedule job on Celery
        try:
            job = chain(
                    run_container.s(
                        uuid,
                        app.config['AWS_SETTINGS'],
                        docker_job_settings
                    )
                ).apply_async(eta=valid_date)
            logger.info("celery job_id: %s " % (job.id))

        except Exception as e:
            logger.debug("unable to schedule job: %s" % e )
            return {'message': 'unable to schedule job, try again latter'}, 500

        # Add job status to redis
        job_status = {
            'id': uuid ,
            'status': 'scheduled',
            'schedule': data['schedule'],
            'docker': {
                'container_id': '',
                'container_status': '',
                'container_exit_code': '',
                'docker_image': data['docker_image'],
                'environment': data['env'],
                'command': data['cmd']
            },
            'aws': {
                'instance_id': '',
                'dns_name': '',
                'ip_address': '',
                'ready': False
            },
            'celery': {
                'job_parent_id': job.id
            }
        }

        jobStore.setJobStatus(uuid, job_status)

        # Return job id
        return {
            'id': uuid,
            'status': 'scheduled',
            'message': 'job successfully scheduled'
        }

class ScheduleList(Resource):
    def get(self):
        jobStore = JobStore()
        return jobStore.getAllJobs()

class ScheduleStatus(Resource):
    def get(self,id):
        jobStore = JobStore()
        status = jobStore.getJobStatus(id)
        if status == None:
            return { 'message': 'not found'}, 404
        return status

class ScheduleCallback(Resource):
    def post(self):
        # Validate Json Schema with required args (action, job_id, instance_id)
        logger = logging.getLogger("ScheduleCallback")
        args = callback_parser.parse_args()
        jobStore = JobStore()
        job_status = jobStore.getJobStatus(args['job_id'])

        if job_status == None:
            return { 'message': 'job not found'}, 404

        if args['action'] == 'update':
            logger.info("received update request: %s, %s" % (args['job_id'], args['instance_id']))
            job_status['aws']['ready'] = True
            jobStore.setJobStatus(args['job_id'], job_status)

            return {'message': 'success'}

        if args['action'] == 'terminate':
            logger.info("received terminate request: %s, %s" % (args['job_id'], args['instance_id']))
            # Schedule job on Celery
            try:
                job = chain(terminate_ec2_spot_instance.s(
                    args['job_id'],
                    args['instance_id'],
                    app.config['AWS_SETTINGS']
                )).apply_async()

                logger.info("celery job_id: %s " % (job.id))
                return {'message': 'success'}

            except Exception as e:
                logger.debug("unable to schedule job: %s" % e )
                return {'message': 'unable to schedule instance termination, try again latter'}, 500


# Generic error Handler
@app.errorhandler(404)
def not_found(error):
    return make_response(
        jsonify({'message': 'not found'}),
        404
    )

# Mapping Resources
api.add_resource(Healthcheck, '/healthcheck', '/api/v1/healthcheck')
api.add_resource(Schedule, '/schedule', '/api/v1/schedule')
api.add_resource(ScheduleList, '/list', '/api/v1/list')
api.add_resource(ScheduleStatus, '/status/<string:id>', '/api/v1/status/<string:id>')
api.add_resource(ScheduleCallback, '/callback', '/api/v1/callback')

if __name__ == '__main__' :
    app.run()
