# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from .wiggle import Entity
from fifo.helper import *

org_fmt = {
    'uuid':
        {'title': 'UUID', 'len': 36, 'fmt': '%36s', 'get': lambda e: d(e, ['uuid'])},
    'name':
        {'title': 'Name', 'len': 10, 'fmt': '%-10s', 'get': lambda e: d(e, ['name'])},
}

org_acct_fmt = {
    'resource':
        {'title': 'Resource UUID', 'len': 36, 'fmt': '%36s', 'get': lambda e: d(e, ['resource'])},
    'action':
        {'title': 'Action', 'len': 8, 'fmt': '%-8s', 'get': lambda e: d(e, ['action'])},
    'timestamp':
        {'title': 'Timestamp', 'len': 16, 'fmt': '%-16s', 'get': lambda e: d(e, ['timestamp'])},
    'date':
        {'title': 'Date & Time', 'len': 19, 'fmt': '%-19s', 'get': lambda e: t(d(e, ['timestamp']))},
}

trigger_fmt = {
    'uuid':
        {'title': 'Trigger UUID', 'len': 36, 'fmt': '%-36s', 'get': lambda e: d(e, ['uuid'])},
    'trigger':
        {'title': 'Trigger', 'len': 15, 'fmt': '%-15s', 'get': lambda e: d(e, ['trigger'])},
    'action':
        {'title': 'Action', 'len': 12, 'fmt': '%-12s', 'get': lambda e: d(e, ['action'])},
    'target':
        {'title': 'Target', 'len': 37, 'fmt': '%-37s', 'get': lambda e: d(e, ['target'])},
    'permission':
        {'title': 'Permission', 'len': 22, 'fmt': '%-22s', 'get': lambda e: perm_p(d(e, ['permission']))},
}

trigger_valid = {
    'vms': ['all', 'list', 'create', 'get', 'delete', 'edit', 'start', 'stop', 'reboot', 'console', 'snapshot',
            'rollback', 'snapshot_delete', 'backup', 'backup_delete'],
    'channels': ['all', 'list', 'create', 'get', 'delete', 'edit'],
    'users': ['all', 'list', 'create', 'get', 'delete', 'edit'],
    'datasets': ['all', 'list', 'create', 'get', 'delete', 'edit']
}


def create(args):
    res = args.endpoint.create(args.name)
    if args.p:
        if res:
            print res['uuid']
        else:
            exit(1)
    else:
        if res:
            print 'Org successfully created: %s' % res['uuid']
        else:
            print 'Org creation failed: %r' % res
            exit(1)


def get_accounting(args):
    start_ts = iso_to_ts(args.start)
    end_ts = iso_to_ts(args.end)
    l = args.endpoint.accounting(args.uuid, start_ts, end_ts)
    if args.H:
        header(args)
    fmt = mk_fmt_str(args)
    if args.raw is True:
        print(json.dumps(l, sort_keys=True, indent=2, separators=(',', ': ')))
    else:
        for e in l:
            if not e:
                print('error!')
                exit(1)
            l = mk_fmt_line(args, e)
            if args.p:
                print(':'.join(l))
            else:
                print(fmt % tuple(l))


def trigger_get(args):
    e = args.endpoint.get(args.uuid)
    if not e:
        exit(1)
    if args.H:
        header(args)
    t = e['triggers']
    fmt = mk_fmt_str(args)
    if args.raw is True:
        print(json.dumps(t, sort_keys=True, indent=2, separators=(',', ': ')))
    else:
        for e in t:
            if not e:
                print('error!')
                exit(1)
            v = t[e]
            v['uuid'] = e
            l = mk_fmt_line(args, v)
            if args.p:
                print(':'.join(l))
            else:
                print(fmt % tuple(l))


def trigger_set(args):
    if args.endpoint.set_trigger(args.uuid, args.action, args.target, args.event, args.base, args.permission):
        print 'Trigger successfully added!'
    else:
        print 'Failed to add trigger!'
        exit(1)


def trigger_delete(args):
    if args.endpoint.delete_trigger(args.uuid, args.trigger_uuid):
        print 'Trigger successfully deleted!'
    else:
        print 'Failed to delete trigger!'
        exit(1)


class Org(Entity):
    def __init__(self, wiggle):
        self._wiggle = wiggle
        self._resource = 'orgs'

    def create(self, name):
        return self._post({'name': name})

    def accounting(self, uuid, start, end):
        params = "start=%s&end=%s" % (start, end)
        return self._get_attr(uuid, "accounting?%s" % params)

    def delete_trigger(self, uuid, target):
        path = "/".join([self._resource, uuid, 'triggers'])
        return self._wiggle.delete(path, target)

    def set_trigger(self, uuid, action, target, event, base, permission):

        path = [self._resource, uuid, 'triggers', event]

        if action in ['join_role', 'join_org']:
            # These do not require permissions
            return self._wiggle.post(path, {
                'action': action,
                'target': target
            })
        else:
            # Need a permission
            if permission is None or permission == "":
                print "No permissions"
                return False

            if base is None or base == "":
                print "No permission base"
                return False

            # If not valid
            if permission not in trigger_valid[base]:
                print "{permission} not valid for {base}".format(permission=permission, base=base)
                return False

            # Deal with "all" permissions
            if "all" == permission:
                p = ['...']
            else:
                p = [permission]

            return self._wiggle.post(path, {
                'action': action,
                'target': target,
                'base': base,
                'permission': p
            })

    @staticmethod
    def add_trigger_parser(subparsers):

        parser_triggers = subparsers.add_parser('triggers', help='Trigger data commands')
        parser_triggers.add_argument('uuid', help='uuid of the element to look at')
        subparsers_triggers = parser_triggers.add_subparsers(help='Trigger commands')

        parser_trigger_get = subparsers_triggers.add_parser('get', help='get triggers')
        parser_trigger_get.add_argument('--raw', '-r', action='store_true',
                                        help='print json array of complete data')
        parser_trigger_get.add_argument('-H', action='store_false')
        parser_trigger_get.add_argument('-p', action='store_true')
        parser_trigger_get.set_defaults(func=trigger_get, fmt=trigger_fmt, fmt_def=trigger_fmt)

        parser_trigger_set = subparsers_triggers.add_parser('set', help='set triggers')
        parser_trigger_set.add_argument('action', help='action to be performed',
                                        choices=['join_role', 'join_org', 'role_grant', 'user_grant'])
        parser_trigger_set.add_argument('target',
                                        help='For join_* actions the role or org to be joined '
                                             'for *_grant the role or user the permission to be granted to')
        parser_trigger_set.add_argument('event', help='event that executes the trigger',
                                        choices=['user_create', 'dataset_create', 'vm_create'])
        parser_trigger_set.add_argument('--base', help='permission base',
                                        choices=['vms', 'users', 'channels', 'datasets'])
        parser_trigger_set.add_argument('--permission', help='string of permissions joined by & (e.g. get&edit')
        parser_trigger_set.set_defaults(func=trigger_set)

        parser_trigger_delete = subparsers_triggers.add_parser('delete', help='delete trigger')
        parser_trigger_delete.add_argument('trigger_uuid', help='trigger uuid to delete')
        parser_trigger_delete.set_defaults(func=trigger_delete)

    def make_parser(self, subparsers):
        parser_orgs = subparsers.add_parser('orgs', help='org related commands')
        parser_orgs.set_defaults(endpoint=self)
        subparsers_orgs = parser_orgs.add_subparsers(help='org commands')
        self.add_metadata_parser(subparsers_orgs)
        self.add_trigger_parser(subparsers_orgs)
        parser_orgs_list = subparsers_orgs.add_parser('list', help='lists orgs')
        parser_orgs_list.add_argument('--fmt', action=ListAction,
                                      default=['uuid', 'name'])
        parser_orgs_list.add_argument('-H', action='store_false')
        parser_orgs_list.add_argument('-p', action='store_true')
        parser_orgs_list.add_argument('--raw', '-r', action='store_true',
                                      help='print json array of complete data')
        parser_orgs_list.set_defaults(func=show_list,
                                      fmt_def=org_fmt)
        parser_orgs_get = subparsers_orgs.add_parser('get', help='gets a org')
        parser_orgs_get.add_argument('uuid')
        parser_orgs_get.set_defaults(func=show_get)
        parser_orgs_delete = subparsers_orgs.add_parser('delete', help='gets a org')
        parser_orgs_delete.add_argument('uuid')
        parser_orgs_delete.set_defaults(func=show_delete)
        parser_orgs_create = subparsers_orgs.add_parser('create', help='creates a Org')
        parser_orgs_create.add_argument('-p', action='store_true')
        parser_orgs_create.add_argument('name')
        parser_orgs_create.set_defaults(func=create)
        parser_orgs_accounting = subparsers_orgs.add_parser('accounting', help='gets accounting information for an org')
        parser_orgs_accounting.add_argument('--fmt', action=ListAction,
                                            default=['resource', 'action', 'timestamp'],
                                            help='Fields to show in the list, valid chances are: resource, action and timestamp')
        parser_orgs_accounting.add_argument('-H', action='store_false',
                                            help='Supress the header.')
        parser_orgs_accounting.add_argument('-p', action='store_true',
                                            help='show in parsable format, rows sepperated by colon.')
        parser_orgs_accounting.add_argument('--raw', '-r', action='store_true',
                                            help='print json array of complete data')
        parser_orgs_accounting.add_argument('uuid')
        parser_orgs_accounting.add_argument('--start', '-s', help='Timestamp of the start of the accounting period')
        parser_orgs_accounting.add_argument('--end', '-e', help='Timestamp of the end of the accounting period')
        parser_orgs_accounting.set_defaults(func=get_accounting, fmt_def=org_acct_fmt)
