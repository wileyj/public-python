from config import Global
import logging
from logger import Logger

Logger()


class Metrics(object):
    def __init__(self, client):
        self.client = client

    def is_active(self, instance_id):
        '''
            Determine if Volume is attached to running instance
        '''
        logging.debug("\tChecking for disk usage on running host: %s" % (instance_id))
        if instance_id in Global.instance_data and Global.instance_data[instance_id]['state'] == 'running':
            return True
        return False

    def is_candidate(self, client, volume_id, instance_id):
        '''
            Make sure the volume is candidate for delete
        '''
        if Metrics().is_active_volume(instance_id):
            metrics = Metrics().metrics(client, volume_id)
            if len(metrics):
                for metric in metrics:
                    if metric['Minimum'] < Global.volume_metric_mininum:
                        logging.debug("\tInactive Volume Tagging Volume for deletion: (%i, %s, %s, %s)" % (metric['Minimum'], Global.instance_data[instance_id]['name'], instance_id, volume_id))
                        return True
                    else:
                        logging.debug("\tActive Volume - Ignoring for deletion: (%i, %s, %s, %s)" % (metric['Minimum'], Global.instance_data[instance_id]['name'], instance_id, volume_id))
                        return False
            else:
                logging.debug("metrics not returned")
                return False
        else:
            logging.debug("%s not active on %s" % (volume_id, instance_id))
            return True

    def metrics(self, client, volume_id):
        '''
            Get volume idle time on an individual volume over `start_date` to today
        '''
        self.volume_metrics_data = client.get_metric_statistics(
            Namespace='AWS/EBS',
            MetricName='VolumeIdleTime',
            Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
            Period=3600,
            StartTime=Global.two_weeks,
            EndTime=Global.today,
            Statistics=['Minimum'],
            Unit='Seconds'
        )
        logging.debug("\t\tReturning datapoints: %s" % (Global.volume_metrics_data['Datapoints']))

    def __repr__(self):
        return repr((self.volume_metrics_data['Datapoints']))
