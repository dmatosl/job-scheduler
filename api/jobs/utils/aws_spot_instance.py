from boto.ec2.connection import EC2Connection
from boto.ec2.connection import EC2ResponseError
import logging
import time
import os

logger = logging.getLogger(__name__)

class AWSSpotInstance():

    __CHECK_INTERVAL = 5   # Seconds
    __CHECK_ATTEMPTS  = 100 # Attemps to create spot Instance

    state = None
    ip_address = None
    dns_name = None
    instance_id = None

    def __init__(self, aws_settings):
        self.cli = EC2Connection(
            aws_access_key_id= aws_settings['AWS_ACCESS_KEY'],
            aws_secret_access_key= aws_settings['AWS_SECRET_ACCESS_KEY']
        )

        self.instance_type = aws_settings['AWS_INSTANCE_TYPE']
        self.instance_count = aws_settings['AWS_INSTANCE_COUNT']
        self.instance_spot_price = aws_settings['AWS_SPOT_PRICE']
        self.instance_tags = aws_settings['AWS_TAGS']
        self.instance_ami = aws_settings['AWS_AMI']
        self.instance_user_data = aws_settings['AWS_USER_DATA']
        self.instance_security_groups = aws_settings['AWS_SECURITY_GROUPS']
        self.aws_secret_access_key = aws_settings['AWS_SECRET_ACCESS_KEY']
        self.aws_access_key = aws_settings['AWS_ACCESS_KEY']
        self.aws_key_name = aws_settings['AWS_KEY_NAME']

    def create_spot_instance(self):
        logger.info('request_spot_instance')
        self.spot_instance = self.cli.request_spot_instances(
            price = self.instance_spot_price,
            count = self.instance_count,
            image_id = self.instance_ami,
            instance_type = self.instance_type,
            key_name = self.aws_key_name,
            user_data = self.instance_user_data,
            security_groups = self.instance_security_groups
        )

        logger.info('adding_tags: %s' % self.instance_tags)
        for spot in self.spot_instance:
            spot.add_tags(self.instance_tags)

        spot_ids = [s.id for s in self.spot_instance]

        for attempt in xrange(self.__CHECK_ATTEMPTS):
            logger.info('attempt number %s' % attempt)
            self.spot_instance = self.cli.get_all_spot_instance_requests(request_ids=spot_ids)
            instance_id = [s.instance_id for s in self.spot_instance if s.instance_id != None]
            logger.info('spot_ids: %s, instance_id: %s' % (spot_ids, instance_id))

            if len(instance_id) == len(spot_ids):
                logger.info('instance_ready')

                try:
                    for instance in self.cli.get_only_instances(instance_ids=instance_id):
                        logger.info('gathering instance information')

                        instance.update()
                        self.state = instance.state
                        self.ip_address = instance.ip_address
                        self.dns_name = instance.public_dns_name
                        self.instance_id = instance.id

                        logger.info('Instance information updated: (state: %s, ip_address: %s, dns_name: %s, instance_id: %s)' % (self.state, self.ip_address, self.dns_name, self.instance_id ))
                    break

                except EC2ResponseError as e:
                    logger.info('aws return 400 (instance not found, ignoring), %s' % e)

            else:
                logger.info('instance not ready ... waiting %s seconds, %s' % (self.__CHECK_INTERVAL, instance_id))
                time.sleep(self.__CHECK_INTERVAL)

        while self.state != 'running':
            logger.info('waiting for instance reach running state: (state: %s, instance_id: %s)' % (self.state, self.instance_id))
            time.sleep(self.__CHECK_INTERVAL)
            self.update_instance(self.instance_id)

        return self.state

    def update_instance(self,instance_id):
        logger.info('updating instance state %s' % instance_id)
        try:
            instance = self.cli.get_only_instances(instance_ids=instance_id)[0]
            self.state = instance.update()
            self.ip_address = instance.ip_address
            self.dns_name = instance.public_dns_name
            self.instance_id = instance.id
        except EC2ResponseError as e:
            logger.info('Instance does not exist, %s' % e)
            return False

        return self.state

    def terminate_spot_instance(self, instance_id):
        logger.info('terminating instance: %s' % instance_id)
        try:
            instance = self.cli.get_only_instances(instance_ids=instance_id)[0]
            instance.terminate()

            while self.state != 'terminated':
                logger.info('waiting for instance reach terminated state: (state: %s)' % self.state)
                time.sleep(self.__CHECK_INTERVAL)
                self.update_instance(instance_id)

        except EC2ResponseError as e:
            logger.info('Instance does not exist, %s' % e)
            return False

        return self.state
