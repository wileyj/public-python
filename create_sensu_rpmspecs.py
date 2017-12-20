#!/usr/bin/env python
import json
import requests
import jinja2
import os
import sys
import re

# python build_gems.py sensu sensu-extensions-debug sensu-extensions-occurrences sensu-extension sensu-extensions sensu-extensions-json sensu-extensions-only-check-output sensu-extensions-ruby-hash sensu-extensions-check-dependencies sensu-plugin sensu-plugins-conntrack sensu-plugins-cpu-checks sensu-plugins-disk-checks sensu-plugins-dns sensu-plugins-filesystem-checks sensu-plugins-memory-checks sensu-plugins-network-checks sensu-plugins-ntp sensu-plugins-process-checks sensu-plugins-load-checks sensu-plugins-logs sensu-plugins-io-checks sensu-plugins-slack sensu-plugins-sms sensu-plugins-ssl sensu-plugins-uchiwa sensu-plugins-uptime sensu-plugins-vmstats sensu-plugins-consul sensu-plugins-graphite sensu-plugins-mongodb sensu-plugins-monit sensu-plugins-nginx sensu-plugins-postgres sensu-plugins-rabbitmq sensu-plugins-redis sensu-plugins-sensu sensu-plugins-java sensu-plugins-snmp sensu-plugins-docker sensu-plugins-cgroups sensu-plugins-tripwire sensu-plugins-haproxy sensu-plugins-mysql sensu-plugins-varnish sensu-plugins-apache sensu-plugins-erlang sensu-plugins-golang sensu-plugins-github sensu-plugins-kubernetes sensu-plugins-jenkins


base_uri = "https://rubygems.org/api/v1/gems"
base_uri_v2 = "https://rubygems.org/api/v2/rubygems"
gems = {}
built = {}
failures = []
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
cwd = os.getcwd()
env = jinja2.Environment(loader=jinja2.FileSystemLoader([cwd]))


def parse_json(data):
    ''' parse the json returned from rubygems.org '''
    if data['name'] == "nokogiri":
        # cheating here, jinja template is having issues with this weird charset. hardcode for now, fix later
        data['info'] = "rubygem " + data['name']
    if data['name'] == "sys-proctable":
        # rubygems.org header is lying. let's force version to 0.9.8 for now
        data['version'] = '0.9.8'
    template_values = {
        'name': data['name'],
        'version': data['version'],
        'summary': data['info'],
        'url': data['homepage_uri'],
        'license': 'GPL',
        'development': [],
        'autoreqprov': '',
        'is_sensu': False,
        'requires': []
    }
    if re.search("plugins-", data['name']) is not None:
        template = "gem_rpmspec_sensu.jinja"
        template_values['autoreqprov'] = 'AutoReqProv: no'
        template_values['is_sensu'] = True
    else:
        template = "gem_rpmspec_sensu.jinja"
    if data['licenses'] is not None:
        if len(data['licenses']) > 0:
            template_values['license'] = data['licenses'][0]

    template_values['description'] = data['info']
    for item in data['dependencies']['runtime']:
        print "item: %s" % (item)
        version_req = item['requirements'].split(" ")[0]
        version = item['requirements'].split(" ")[1]
        if version_req == "~>":
            version_req = ">="
        if version == "0":
            required_package = {'name': item['name']}
        else:
            required_package = {'name': item['name'], 'version': version_req + ' ' + version}
        template_values['requires'].append(required_package)
        print "\t new version_req: %s" % (version_req)
        if not gems.get(item['name']):

            gems[item['name']] = item['requirements'].split(" ")[1]
    for item in data['dependencies']['development']:
        if item['requirements'].split(" ")[1] == "0":
            development_package = {'name': item['name']}
        else:
            development_package = {'name': item['name'], 'version': item['requirements'].split(" ")[1]}
        template_values['development'].append(development_package)
    template_dest = "specs/rubygem-" + template_values['name'] + "-" + data['version'] + ".spec"
    if os.path.isfile(template_dest) and os.access(template_dest, os.R_OK):
        print "Found Existing RPM: %s" % (template_dest)
        built[template_values['name']] = True
        if gems.get(template_values['name']):
            del gems[template_values['name']]
    else:
        built[template_values['name']] = True
        write_spec(template_values, cwd + "/" + template, cwd + "/" + template_dest)
    print "\t(%i) gems: %s" % (len(gems), gems)


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


def get_gem_data(gem, version):
    ''' use v2 of the rubygem.org api'''
    version = version.replace(",", "")
    print "url: %s" % (base_uri_v2 + '/' + gem + '/versions/' + version + '.json')
    req = requests.get(base_uri_v2 + '/' + gem + '/versions/' + version + '.json')
    if req.status_code is 200:
        data = json.loads(req.content)
        parse_json(data)
    else:
        failures.append(gem)


def get_gem_data_v1(gem):
    ''' use v1 of the rubygem.org api'''
    print "url: %s" % (base_uri + '/' + gem)
    req = requests.get(base_uri + '/' + gem)
    if req.status_code is 200:
        data = json.loads(req.content)
        parse_json(data)
    else:
        failures.append(gem)


def parse_gems(gems):
    ''' cleanup our list of dependent gems '''
    if len(gems) > 0:
        for gem in list(gems):
            if gems.get(gem):
                del gems[gem]
            if not built.get(gem):
                gem_name = gem
                get_gem_data_v1(gem_name)
                parse_gems(gems)


if __name__ == "__main__":
    ''' main '''
    sys.argv[1:]
    arguments = sys.argv[1:]
    count = len(arguments)
    if count > 0:
        for base_gem in arguments[0:]:
            print "Building Gem: %s" % (base_gem)
            req = requests.get(base_uri + '/' + base_gem)
            data = json.loads(req.content)
            get_gem_data(data['name'], data['version'])
            if gems and len(gems) > 0:
                parse_gems(gems)
            if len(failures) > 0:
                print "failures: %s" % (failures)
    else:
        print "No args provided"
