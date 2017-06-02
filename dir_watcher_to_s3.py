#!/usr/bin/python
""" docstring """
import os
import datetime
import subprocess
import argparse
import boto3

resource = boto3.resource('s3')
client = resource.meta.client
s3_client = boto3.client('s3')

def upload_to_s3(filename, bucketname, tmpdir):
    """ docstring """
    timestamp = datetime.datetime.utcnow().isoformat()
    file_stat = os.stat(filename)
    local_size = file_stat.st_size
    s3_filename = os.path.basename(filename)
    print ""
    print "Uploading at %s" % (timestamp)
    print "LocalFile: %s" % (filename)
    print "Bucket: %s" % (bucketname)
    print "S3File: %s" % (s3_filename)
    client.upload_file(filename, bucketname, s3_filename)
    response = s3_client.list_objects(Bucket=bucketname, Prefix=s3_filename)['Contents']
    remote_size = response[0]['Size']

    print "Uploaded File Size: ", remote_size
    if remote_size == local_size:
        print "\tUploaded file Matches local ( %s/%s )" % (remote_size, local_size)
        print "\tDeleting Local file %s " % (filename)
        #os.remove(filename)
        tmp_path = tmpdir+"/"+s3_filename
        os.rename(filename, tmpdir)
        return 0
    else:
        print "\tUploaded file size doesn't match local file size "
        print "\tLocal:  %s size: %s" % (filename, local_size)
        print "\tRemote: %s size: %s" % (s3_filename, remote_size)
        return -1

def get_files(directory):
    """ docstring """
    file_paths = []
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        file_paths.append(filepath)
    return file_paths

def sync_dir(directory, bucket, profile, tmpdir):
    """ docstring """
    # no boto3 method for syncing a dir, so we'll fork to aws cli
    command = "/usr/local/bin/aws --profile "+profile+" s3 sync "+directory+"/ s3://"+bucket
    #print "aws --profile %s s3 sync %s/ s3://%s" % (profile, directory, bucket)
    print "Running command: %s" % (command)
    subprocess.call(command, shell=True)
    tmp_path = tmpdir+"/"
    for filename in os.listdir(directory):
        source_path = os.path.join(directory, filename)
        dest_path = os.path.join(tmpdir, filename)

        print "rename: %s %s" % (source_path, dest_path)
        os.rename(source_path, dest_path)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dir',
        nargs='?',
        metavar='',
        default="",
        help="type: fully qualified path"
    )
    parser.add_argument(
        '--bucket',
        nargs='?',
        metavar='',
        default="",
        help="type: bucketname"
    )
    parser.add_argument(
        '--tmpdir',
        nargs='?',
        metavar='',
        default="",
        help="type: tmp dir to hold files for 3 days"
    )
    parser.add_argument(
        '--type',
        nargs='?',
        metavar='',
        default="",
        help="type: upload/sync"
    )
    parser.add_argument(
        '--profile',
        nargs='?',
        metavar='',
        default="default",
        help="type: aws config profile to use"
    )
    args = parser.parse_args()
    if not args.dir or not args.bucket or not args.tmpdir or not args.type:
        print "[ Error ] - Missing args"
        print "\t ex %s --dir /tmp/dir --bucket data-dir --tmpdir /var/tmp/dir --iam_profile default --type upload" % (os.path.basename(__file__))
        print "\t ex %s --dir /tmp/dir --bucket data-dir --tmpdir /var/tmp/dir --iam_profile default --type sync" % (os.path.basename(__file__))
        exit(1)
    if args.type == "sync":
        sync_dir(args.dir, args.bucket, args.profile, args.tmpdir)
    else:
        list_files = get_files(args.dir)
        for item in list_files:
            upload_to_s3(item, args.bucket, args.tmpdir)
