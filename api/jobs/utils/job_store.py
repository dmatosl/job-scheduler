import os
import json
from redis import Redis

class JobStore():
    __key_prefix = 'job:meta:'

    def __init__(self):
        self.red = Redis(
            host=os.environ['REDIS_HOST'],
            port=os.environ['REDIS_PORT']
        )

    def getJobStatus(self, job_id):
        job = self.__key_prefix + job_id
        job_data = self.red.get(job)
        if job_data is None:
            return None

        return json.loads(self.red.get(job))

    def getAllJobs(self):
        all_keys = self.red.keys(pattern=self.__key_prefix + "*")
        job_list = []
        for key in all_keys:
            data = json.loads(self.red.get(key))
            job_list.append({
                'id': data['id'],
                'status': data['status'],
                'schedule': data['schedule']})
        all_jobs = {'jobs': job_list}

        return all_jobs

    def setJobStatus(self, job_id, data):
        job = self.__key_prefix + job_id
        return self.red.set(job, json.dumps(data))
