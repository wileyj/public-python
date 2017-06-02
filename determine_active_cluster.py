"""
Use boto to determine the active app prod cluster index
"""


import boto3


def parseCNAMEAlias(alias, app):
    tokens = alias.split('.')
    tokens = tokens[0].split('-')

    if len(tokens) < 2:
        print 'Unknown CNAME alias format:', alias
        return -3

    if tokens[0] != app:
        print 'App != ', app, ' : ', alias
        return -2

    if tokens[1] != "prod":
        print 'Environment != prod', alias
        return -1

    # Index not provided
    if len(tokens) < 3:
        return 0

    return int(tokens[2])


def determineActiveIndex(app="app", region="us-west-1"):
    print "Determining active prod cluster index for application", app

    route53 = boto3.client('route53')

    # Remember that a fully qualified domain ends with a .
    zoneName = 'local.com.'
    domain = ".".join([app, zoneName])

    query = {'StartRecordName': domain, 'StartRecordType': 'CNAME'}
    for zone in route53.list_hosted_zones()['HostedZones']:
        if zone['Name'] == zoneName:
            query['HostedZoneId'] = zone['Id']
            break

    if 'HostedZoneId' not in query:
        print "Couldn't find ID for zone", zoneName
        return -1

    records = route53.list_resource_record_sets(**query)

    for record in records['ResourceRecordSets']:
        if record['Name'] == domain:
            return parseCNAMEAlias(record['AliasTarget']['DNSName'], app)

    return -1


if __name__ == "__main__":
    index = determineActiveIndex()
    if index < 0:
        import sys
        print 'Could not determine active index.'
        sys.exit(1)
    print index

