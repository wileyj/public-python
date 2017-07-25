import boto3
import logging
from logger import Logger

Logger()


class conn():
    def __init__(self, service, region):
        logging.error("Initiating Connection to service(%s) in region(%s)" % (service, region))
        client = boto3.client(service, region_name=region)
        self.client = client

    def __repr__(self):
        return repr((self.client))
