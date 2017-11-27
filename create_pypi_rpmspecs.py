# https://pypi.python.org/pypi/Jinja2/json
# https://pypi.python.org/pypi/<package_name>/<version>/json
# initial modules:
# python build_pymodules.py amqp argparse awscli backports_abc backports.ssl_match_hostname boto3 celery certifi chardet docker docker-py docker-pycreds flower futures GitPython gnupg idna Jinja2 json libcloud libnacl M2Crypto MarkupSafe mock msgpack msgpack-pure paramiko passlib pip pycrypto pytz PyYAML pyzmq requests singledispatch six tornado unittest2 urllib3 thefuck

#         thefuck
#         prometheus
#

import json
import requests
import os
import jinja2
import sys
import re
from os.path import splitext

base_uri = "https://pypi.python.org/pypi/"
base_uri_version = ""
base_module = "Jinja2"
modules = {}
built = {}
failures = []
template_values = {}
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
cwd = os.getcwd()
env = jinja2.Environment(loader=jinja2.FileSystemLoader([cwd]))
template = "pypi_rpmspec.jinja"
template3 = "pypi3_rpmspec.jinja"


def parse_json(data):
    name = data['info']['name']
    license = data['info']['license']
    if data['info']['license'] == "":
        license = "GPL"
    if data['info']['name'] == "flaky":
        license = "Apache"
    url = data['info']['home_page']
    version = data['info']['version']
    # description = data['info']['description']
    template_dest = "specs/python/python-" + name + "-" + version + ".spec"
    template3_dest = "specs/python/python3-" + name + "-" + version + ".spec"
    if (
        os.path.isfile(template_dest) and
        os.access(template_dest, os.R_OK) and
        os.path.isfile(template3_dest) and
        os.access(template3_dest, os.R_OK)
    ):
        print "\tFound Existing RPM: %s" % (template_dest)
        built[name] = True
        if modules.get(name):
            del modules[name]
    else:
        built[name] = True
        template_values = {
            'name': name,
            'lc_name': name.lower(),
            'version': version,
            'url': url,
            'license': license,
            'source': '',
            # 'description': description,
            'with_python3': 0,
            'with_alinux': 1,
            'compression': '',
            'extension': '',
            'requires': []
        }
        if 'requires_dist' in data['info']:
            for item in data['info']['requires_dist']:
                req_name = item.split(" ")[0].replace(";", "")
                required_package = {'name': req_name}
                template_values['requires'].append(required_package)
                if (
                    not modules.get(req_name) and
                    req_name != "multidict" and
                    req_name != "win_inet_pton"
                ):
                    modules[req_name] = req_name
        for i in range(len(data['releases'][version])):
            if data['releases'][version][i]['packagetype'] == "sdist":
                print "\t** found SDIST(%s) url: %s" % (data['releases'][version][i]['packagetype'], data['releases'][version][i]['url'])
                template_values['source'] = data['releases'][version][i]['url']
                ext = splitext(data['releases'][version][i]['url'])[1]
                print "\t** Extension: %s" % (ext)
                if ext == ".zip":
                    compress_type = "zip"
                    extension = "zip"
                else:
                    compress_type = "tar"
                    extension = "tar.gz"
                # print "release: %s" % (release)
                template_values['compression'] = compress_type
                template_values['extension'] = extension
                break
        for lang in data['info']['classifiers']:
            if re.search("Programming Language :: Python :: 3", lang) is not None:
                print "\t ** BUILD Python 3 ..."
                write_spec(template_values, cwd + "/" + template3, cwd + "/" + template3_dest)
                break
        write_spec(template_values, cwd + "/" + template, cwd + "/" + template_dest)
        if len(modules) > 0:
            print "\t %i dependent modules:" % (len(modules))
            for item in modules:
                req_name = item.split(" ")[0].replace(";", "")
                print "\t\t %s (%s)" % (req_name, modules[req_name])


def write_spec(template_values, template_source, template_dest):
    ''' write the rpm spec file from jinja template '''
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(["/"]))
    template = jinja_env.get_template(template_source)
    result = template.render(template_values)
    os.open(template_dest, os.O_CREAT)
    fd = os.open(template_dest, os.O_RDWR)
    os.write(fd, result)
    file_stat = os.stat(template_dest)
    file_size = file_stat.st_size
    print "\tCreated RPM Specfile: %s ( %s )" % (template_dest, file_size)
    os.close(fd)
    return 0


def get_module_data_v1(module):
    print "\nBuilding Module: %s" % (module)
    url = base_uri + module + "/json"
    print "\t ** module: %s" % (module)
    print "\t ** url: %s" % (url)
    req = requests.get(
        url,
        timeout=1
    )
    if req.status_code is 200:
        data = json.loads(req.content)
        print "\t ** version: %s" % (data['info']['version'])
        parse_json(data)
    else:
        print "\t failing module: %s" % (module)
        failures.append(module)


def parse_modules(modules):
    ''' cleanup our list of dependent gems '''
    if len(modules) > 0:
        for module in list(modules):
            if modules.get(module):
                del modules[module]
            if not built.get(module):
                get_module_data_v1(module)
                parse_modules(modules)


if __name__ == "__main__":
    sys.argv[1:]
    arguments = sys.argv[1:]
    count = len(arguments)
    if count > 0:
        for base_module in arguments[0:]:
            get_module_data_v1(base_module)
            if modules and len(modules) > 0:
                for i in modules:
                    print "\t *** dependency: %s (%s)" % (i, modules[i])
                parse_modules(modules)
            if len(failures) > 0:
                print "Failures:"
                for item in failures:
                    print "\t%s" % (item)
    else:
        print "No args provided"
