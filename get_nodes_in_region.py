"""
Use boto to find all nodes running in a specific region
"""


from boto3.session import Session

from determine_active_cluster import determineActiveIndex


def getNodes(region="us-west-2"):
    """ Get a sequence of private ip addresses for the nodes in an app cluster
    in a region, per environment. """

    # Use boto to get all reservations
    session = Session()
    ec2 = session.resource('ec2', region_name=region)

    # Only list running instances
    filters = [{'Name':'instance-state-name', 'Values':['running']}]

    # Distill instance objects into dicts
    ret = [];
    for instance in ec2.instances.filter(Filters=filters):
        if instance.tags is None:
            continue
        for tag in instance.tags:
            if tag['Key'] != "Name":
                continue
            ret.append({
                "id": instance.id,
                "ip": instance.private_ip_address,
                "name": tag['Value'],
                "region": region
            })

    return ret;


def getIPsOfActiveNodes(env, regions, app="app"):
    ips = []
    activeIndex = 1

    if env == "prod":
        activeIndex = determineActiveIndex()

    for region in regions:
        for item in getNodes(region):
            name = item["name"]
            tokens = name.split("-")

            if len(tokens) < 2:
                continue

            appName = tokens[0]
            envName = tokens[1]

            if env != envName or appName != app:
                continue

            if len(tokens) > 2:
                # If the name has an index, check it against active
                if int(tokens[2]) == activeIndex:
                    ips.append(item["ip"])
            else:
                # If not just add it
                ips.append(item["ip"])

    print "Found {} nodes in {} cluster {}".format(len(ips), env, activeIndex)

    return ips


if __name__ == "__main__":
    for node in getNodes():
        print node['name']

