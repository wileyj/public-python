
import random

from get_nodes_in_region import getNodes

def randomIPFromCluster(env="dev", index=0):

    region = "us-west-2"

    if env == "prod":
        region = "us-west-1"

    nodes = getNodes(region)
    ips = set()

    for node in nodes:
        tokens = node["name"].split("-")

        if tokens[0] != "app" or tokens[1] != env:
            continue

        idx = 0
        if len(tokens) > 2:
            idx = int(tokens[2])

        if index == idx:
            ips.add(node["ip"])

    return random.sample(ips, 1)[0]


def usage():
    print "./script.py <env> [index]"


if __name__ == "__main__":
    import sys
    env = "dev"
    index = 0
    if len(sys.argv) > 1:
        env = sys.argv[1]
    if len(sys.argv) > 2:
        index = int(sys.argv[2])
    print randomIPFromCluster(env, index)
