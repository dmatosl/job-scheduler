from docker import Client
from docker.errors import NotFound
import logging

logger = logging.getLogger(__name__)

class DockerContainer():

    def __init__(self, host, port=2376):
        self.cli = Client(base_url="http://%s:%s" %(host, port), version='auto')
        self.cli.ping()

    def get_docker_instance(self):
        return self.cli

    def pull_image(self, docker_image):
        for p in self.cli.pull(docker_image, stream=True, decode=True):
            if 'status' in p:
                if 'Downloaded newer image for' in p['status']:
                    return True
                if 'Image is up to date for' in p['status']:
                    return True
        return False

    def run_container(self, docker_image, env, cmd):
        if self.pull_image(docker_image):

            if type(env) == str or type(env) == unicode:
                if env.strip() == '':
                    env = None

            if cmd.strip() == '':
                cmd = None

            try:
                container = self.cli.create_container(
                    docker_image,
                    environment=env,
                    command=cmd
                )

                self.cli.start(resource_id=container)

                container_status = self.cli.containers(
                    all=True,
                    filters={'id': container['Id']}
                )[0]

                return container_status
            except NotFound as e :

                logger.info('Failed to run container: %s' % e)
                return None
        else:
            return None
