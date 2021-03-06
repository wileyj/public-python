from config import Global
from metrics import Metrics
import logging
from logger import Logger

Logger()


class Volume(object):
    def __init__(self, client, dry_run):
        self.client = client
        self.dry_run = dry_run

    def find(self, cloudwatch_client, instance, volume, hourly, persist):
        '''
            find_volumes function
        '''
        logging.critical("\n*** Retrieving volumes")
        if not instance and not volume:
            my_volumes = self.client.describe_volumes()['Volumes']
        else:
            if instance:
                my_volumes = sorted(
                    self.client.describe_volumes(
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
                    self.client.describe_volumes(
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
            logging.critical("\tChecking if volume is attached (%s)" % (volume['VolumeId']))
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
                    if Metrics(cloudwatch_client, self.dry_run).is_candidate(volume['VolumeId'], attached['InstanceId']):
                        logging.critical("\t\tCandidate Volume (%s, %s)" % (attached['InstanceId'], volume['VolumeId']))
                        logging.critical("\t\tTagging Volume for deletion (%s, %s)" % (attached['InstanceId'], volume['VolumeId']))
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
                        if not self.dry_run:
                            # logging.error("Tagging Volume %s with {'Delete': 'True'}" % (volume['VolumeId']))
                            logging.critical("Tagging Volume %s with {'Delete': 'True'}" % (volume['VolumeId']))
                            # self.client.create_tags(
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
                            logging.critical("\t\tBacking up Volume (%s) with description (%s)" % (volume['VolumeId'], Global.instance_data[attached['InstanceId']]['name']))
                            logging.critical("\t************")
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
