from flask import Flask, make_response, jsonify, request
from flask_restful import Api, Resource, reqparse, abort
from celery import Celery
from celery.result import AsyncResult
from celery.task.control import inspect
from celery import chain
from jobs.tasks import *
from datetime import datetime
import logging
import time

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

# Celery configuration
celery = Celery("jobs", broker=app.config['CELERY_BROKER_URL'],
                    backend=app.config['CELERY_BACKEND'])
celery.conf.update(app.config)
celery.autodiscover_tasks(['jobs'])

# Request Parser
schedule_parser = reqparse.RequestParser()
schedule_parser.add_argument('docker_image',type=str, required=True, location='json')
schedule_parser.add_argument('schedule',type=str, required=True, location='json')
schedule_parser.add_argument('cmd',type=str, required=False, location='json')

class Healthcheck(Resource):
    def get(self):
        return {'message': 'live'}

class Schedule(Resource):
    #decorators = [
    #    jsonschema.validate('schedule', 'post_schedule')
    #]

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

        # Validate date format
        try:
            valid_date = datetime.strptime(args['schedule'], "%Y-%m-%d %H:%M:%S")
        except (KeyError, TypeError, ValueError) as e:
            logger.debug("Date format validation Exception: %s" % e)
            return {'message': {'schedule': 'schedule does not match format YYYY-mm-dd xx:yy:zz'}}, 400

        # Validate env type
        if 'env' in data:
            if type(data['env']) != type([]) :
                logger.debug("Env validation is not a list: (type: %s, data: %s)" % (type(data['env']), data) )
                return {'message': {'env': 'must be a list'}}, 400

        # Schedule job on Celery
        try:
            #job = my_task.apply_async(args=[10,10], eta=valid_date)
            job = chain(
                    run_ec2_spot_instance.s(app.config['AWS_SETTINGS']) |
                    run_docker_container.s(data['docker_image'],data['env'],data['cmd']) |
                    terminate_ec2_spot_instance.s()
                ).apply_async(eta=valid_date)
        except Exception as e:
            logger.debug("unable to schedule job: %s" % e )
            return {'message': 'unable to schedule job, try again latter'}, 500

        # Return job id
        return {
            "id": job.parent.parent.id,
            "message": "job successfully scheduled"
        }

class ScheduleList(Resource):
    def get(self):
        pass

class ScheduleStatus(Resource):
    def get(self,id):
        job = inspect(id)


class ScheduleCallback(Resource):
    def post(self,id):
        pass

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
