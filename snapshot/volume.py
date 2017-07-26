from config import Global
import logging
from logger import Logger

Logger()


class Volume(object):
    def find(self, client, instance, volume, dry_run, hourly, persist):
        '''
            find_volumes function
        '''
        logging.critical("\n*** Retrieving volumes")
        if not instance and not volume:
            my_volumes = client.describe_volumes()['Volumes']
        else:
            if instance:
                my_volumes = sorted(
                    client.describe_volumes(
                        Filters=[{
                            'Name': 'volume-id',
                            'Values': Global.instance_data[instance]['volumes']
                        }]
                    )['Volumes'],
                    key=lambda x: (
                        x['VolumeId']
                    ),
                    reverse=True
                )
            else:
                my_volumes = sorted(
                    client.describe_volumes(
                        Filters=[{
                            'Name': 'volume-id',
                            'Values': [volume]
                        }]
                    )['Volumes'],
                    key=lambda x: (
                        x['VolumeId']
                    ),
                    reverse=True
                )
        for volume in my_volumes:
            tag_delete = False
            try:
                for tag in volume['Tags']:
                    if tag['Key'] == 'Delete':
                        tag_delete = tag['Value']
            except:
                pass
            for attached in volume['Attachments']:
                Global.all_volumes[volume['VolumeId']] = {
                    'id': volume['VolumeId'],
                    'attachment_id': attached['VolumeId'],
                    'instance_id': attached['InstanceId'],
                    'snapshot_id': volume['SnapshotId'],
                    'device': attached['Device'],
                    'state': volume['State'],
                    'size': volume['Size'],
                    'date': volume['CreateTime']
                }
                Global.volume_snapshot_count[attached['VolumeId']] = {'count': 0}
                if tag_delete == 'True':
                    Global.volume_data[volume['VolumeId']] = {
                        'id': volume['VolumeId'],
                        'attachment_id': attached['VolumeId'],
                        'instance_id': attached['InstanceId'],
                        'snapshot_id': volume['SnapshotId'],
                        'device': attached['Device'],
                        'state': volume['State'],
                        'size': volume['Size'],
                        'date': volume['CreateTime']
                    }
                else:
                    if Volume().is_candidate(volume['VolumeId'], attached['InstanceId']):
                        logging.debug("\t\tCandidate Volume (%s, %s)" % (attached['InstanceId'], volume['VolumeId']))
                        logging.debug("\t\tTagging Volume for deletion (%s, %s)" % (attached['InstanceId'], volume['VolumeId']))
                        Global.volume_data[volume['VolumeId']] = {
                            'id': volume['VolumeId'],
                            'attachment_id': attached['VolumeId'],
                            'instance_id': attached['InstanceId'],
                            'snapshot_id': volume['SnapshotId'],
                            'device': attached['Device'],
                            'state': volume['State'],
                            'size': volume['Size'],
                            'date': volume['CreateTime']
                        }
                        if not dry_run:
                            # logging.error("Tagging Volume %s with {'Delete': 'True'}" % (volume['VolumeId']))
                            logging.critical("Tagging Volume %s with {'Delete': 'True'}" % (volume['VolumeId']))
                            # client.create_tags(
                            #     Resources=[volume['VolumeId']],
                            #     Tags=[{
                            #         'Key': 'Delete',
                            #         'Value': 'True'
                            #     }]
                            # )
                        else:
                            # logging.error("(dry-run) Tagging Volume %s with {'Delete': 'True'}" % (volume['VolumeId']))
                            logging.critical("(dry-run) Tagging Volume %s with {'Delete': 'True'}" % (volume['VolumeId']))
                    else:
                        if len(volume['Attachments']) > 0:
                            if hourly:
                                desc = Global.short_hour
                            else:
                                desc = Global.short_date
                            if persist:
                                persist = True
                            else:
                                persist = False
                            # here we flag a volume for backup
                            if attached['InstanceId'] not in Global.instance_data:
                                desc = desc + ":" + attached['InstanceId']
                            else:
                                desc = desc + ":" + Global.instance_data[attached['InstanceId']]['name'].replace(" - ", "-")
                            desc = desc.replace(")", "")
                            desc = desc.replace("(", "")
                            desc = desc.replace(" ", "-")
                            Global.snapshot_volumes[volume['VolumeId']] = {
                                'id': volume['VolumeId'],
                                'instance_id': attached['InstanceId'],
                                'date': volume['CreateTime'],
                                'desc': desc + ":" + attached['Device'] + ":" + volume['VolumeId'],
                                'old_desc': desc + ":" + attached['Device'],
                                'persist': persist,
                                'hourly': hourly
                            }
        logging.critical("\tTotal Volumes discovered: %s" % (len(my_volumes)))
        logging.critical("\tTotal Volumes tagged for deletion: %i" % (len(Global.volume_data)))
        logging.critical("\tTotal Volumes tagged for backup: %i" % (len(Global.snapshot_volumes)))
        return True

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
        if Volume().is_active_volume(instance_id):
            metrics = Volume().metrics(client, volume_id)
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
        volume_metrics_data = client.get_metric_statistics(
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
        return volume_metrics_data['Datapoints']
