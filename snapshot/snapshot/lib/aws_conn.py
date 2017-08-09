import boto3
import logging
from logger import Logger

Logger()


class conn(object):
    def ec2(self, region):
        '''
            Class to broker connection to aws
        '''
        logging.critical("Initiating Connection to service('cloudwatch') in region(%s)" % (region))
        self.client = boto3.client('ec2', region_name=region)
        return self.client

    def cloudwatch(self, region):
        '''
            Class to broker connection to aws
        '''
        logging.critical("Initiating Connection to service('cloudwatch') in region(%s)" % (region))
        self.client = boto3.client('cloudwatch', region_name=region)
        return self.client
    # def __repr__(self):
    #     return repr((self.client))
# class conn():
#     def ec2(self, service, region):
#         ec2_client = boto3.client(service, region_name=region)
#         return ec2_client
