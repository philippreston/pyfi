#! /usr/bin/env python3.3
import configparser
import os
import sys
import argparse
from api.wiggle import Wiggle, VM, Package
from pprint import pprint
import json

# We need to add a own action for lists as arguments
class ListAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.split(','))



#First we initialize our configuration read the data and generate a default if needed

config = configparser.ConfigParser()
config_file = os.environ.get('HOME') + "/.fifo"

config.read(config_file);

if not config.has_section('GENERAL'):
    print ("fifo client is not configured creating an example config at: " + config_file)
    config.add_section('GENERAL')
    config.set('GENERAL', 'active', 'default')
    config.add_section('default')
    config.set('default', 'host', '127.0.0.1')
    config.set('default', 'user', 'test')
    config.set('default', 'pass', 'test')
    with open(config_file, 'w') as configfile:
        config.write(configfile)
        exit(1)

active_config = config.get('GENERAL', 'active')

if not config.has_section(active_config):
    print("Active configuration " + active_config + " does not exist")
    exit(1)

host = config.get(active_config, 'host')
user = config.get(active_config, 'user')
pw = config.get(active_config, 'pass')

token = False

if config.has_option(active_config, 'token'):
    token = config.get(active_config, 'token')


# Now we initialize our wiggle endpoint
wiggle = Wiggle(host, user, pw, token)

#We check if we can get a valid token from wiggle and store it on our config
if wiggle.get_token():
    config.set('default', 'token', wiggle.get_token())
with open(config_file, 'w') as configfile:
    config.write(configfile)


# Gets a value from a nested hash map or returns a given default if the value
# is not present
def d(o, p, deflt="-"):
    if p == []:
        return o
    else:
        k = p[0]
        if k in o:
            return d(o[k], p[1:], deflt)
        else:
            return deflt


#Returns the ip of a vm (first ip in the networks)
def vm_ip(e):
    n = d(e, ['config', 'networks'], [])
    if len(n) > 0:
        return n[0]['ip']
    else:
        return "-"


#Define the Diferent format options for the list sections
vm_fmt = {
    'uuid':
    {'title': 'UUID', 'len': 36, 'fmt': "%36s", 'get': lambda e: d(e, ['uuid'])},
    'alias':
    {'title': 'alias', 'len': 10, 'fmt': "%-10s", 'get': lambda e: d(e, ['config', 'alias'])},
    'ip':
    {'title': 'IP', 'len': 15, 'fmt': "%15s", 'get': vm_ip},
    'state':
    {'title': 'state', 'len': 15, 'fmt': "%-15s", 'get': lambda e: d(e, ['state'])},
    'hypervisor':
    {'title': 'hypervisor', 'len': 20, 'fmt': "%-20s", 'get': lambda e: d(e, ['hypervisor'])},
}

pkg_fmt = {
    'uuid':
    {'title': 'UUID', 'len': 36, 'fmt': "%36s", 'get': lambda e: d(e, ['uuid'])},
    'name':
    {'title': 'Name', 'len': 10, 'fmt': "%-10s", 'get': lambda e: d(e, ['name'])},
    'cpu_cap':
    {'title': 'CPU cap', 'len': 10, 'fmt': "%-10s", 'get': lambda e: str(d(e, ['cpu_cap'])) + "%"},
    'quota':
    {'title': 'Quota', 'len': 10, 'fmt': "%-10s", 'get': lambda e: str(d(e, ['quota'])) + " GB"},
    'ram':
    {'title': 'RAM', 'len': 10, 'fmt': "%-10s", 'get': lambda e: str(d(e, ['ram'])) + " MB"},
}


# Helper function to generate a formatstring out of the format definition and the selected fields
def mk_fmt_str(args):
    s = ""
    for k in args.fmt:
        s = s + args.fmt_def[k]['fmt'] + " "
    return s

# Helper function to generate the format values for one of the lines.
def mk_fmt_line(args, e):
    r = []
    for k in args.fmt:
        r.append(args.fmt_def[k]['get'](e))
    return r

# Prints the header for a list opperation based on the selected format
def header(args):
    fmt = mk_fmt_str(args)
    r = []
    for k in args.fmt:
        r.append(args.fmt_def[k]['title'])
    if args.p:
        print(":".join(r))
    else:
        print(fmt % tuple(r))
    r = []
    if not args.p:
        for k in args.fmt:
            r.append("-" * args.fmt_def[k]['len'])
        print(fmt % tuple(r))


# Shows the data when get was selected, outputs it in JSON
def show_get(args):
    e = args.endpoint.get(args.uuid)
    if not e:
        print("error!")
        exit(1)
    if 'map_fn' in args:
        e = args.map_fn(e)
    print(json.dumps(e, sort_keys=True, indent=2, separators=(',', ': ')))


# Shows the data when list was selected.
def show_list(args):
    l = args.endpoint.list()
    if not l:
        print("error!")
        exit(1)
    if args.H:
        header(args)
    fmt = mk_fmt_str(args)
    for uuid in l:
        args.uuid = uuid
        e = args.endpoint.get(uuid)
        if not e:
            print("error!")
            exit(1)
        l = mk_fmt_line(args, e)
        if args.p:
            print(":".join(l))
        else:
            print(fmt%tuple(l))

# Helper functions to format the different getters for VM's
def vm_map_fn(vm):
    return(vm['config'])

def vm_info_map_fn(vm):
    return(vm['info'])


# Parse the arguments ...

parser = argparse.ArgumentParser(description='FiFo API client.')

subparsers = parser.add_subparsers(help='sub commands')

## VMS
parser_vms = subparsers.add_parser('vms', help='vm related commands')
parser_vms.set_defaults(endpoint=VM(wiggle))

subparsers_vms = parser_vms.add_subparsers(help='vm commands')

parser_vms_list = subparsers_vms.add_parser('list', help='lists a vm')
parser_vms_list.add_argument("--fmt", action=ListAction, default=['uuid', 'hypervisor', 'alias', 'state'])
parser_vms_list.add_argument("-H", action='store_false')
parser_vms_list.add_argument("-p", action='store_true')
parser_vms_list.set_defaults(func=show_list,
                             fmt_def=vm_fmt)

parser_vms_get = subparsers_vms.add_parser('get', help='gets a vm')
parser_vms_get.add_argument("uuid")
parser_vms_get.set_defaults(func=show_get,
                            map_fn=vm_map_fn)

parser_vms_info = subparsers_vms.add_parser('info', help='gets a vm')
parser_vms_info.add_argument("uuid")
parser_vms_info.set_defaults(func=show_get,
                             map_fn=vm_info_map_fn)

## Packages
parser_pkgs = subparsers.add_parser('packages', help='vm related commands')
parser_pkgs.set_defaults(endpoint=Package(wiggle))

subparsers_pkgs = parser_pkgs.add_subparsers(help='vm commands')

parser_pkgs_list = subparsers_pkgs.add_parser('list', help='lists packages')
parser_pkgs_list.add_argument("--fmt", action=ListAction, default=['uuid', 'name', 'ram', 'cpu_cap', 'quota'])
parser_pkgs_list.add_argument("-H", action='store_false')
parser_pkgs_list.add_argument("-p", action='store_true')
parser_pkgs_list.set_defaults(func=show_list,
                              fmt_def=pkg_fmt)

parser_pkgs_get = subparsers_pkgs.add_parser('get', help='gets a package')
parser_pkgs_get.add_argument("uuid")
parser_pkgs_get.set_defaults(func=show_get,
                             fmt_def=pkg_fmt)

args = parser.parse_args(sys.argv[1:])
if 'func' in args:
    args.func(args)
else:
    parser.print_help()
