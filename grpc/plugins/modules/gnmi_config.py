# (c) 2020 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: gnmi_config
author:
    - "Hans Thienpondt (@HansThienpondt)"
    - "Sven Wisotzky (@wisotzky)"
short_description: Modify nodal configuration using a single gNMI Set operation
description:
    - gRPC is a high performance, open-source universal RPC framework.
    - This module allows the user to configure a networking device.
    - The C(--check) is not supported, as there is no onbox suppport for
      validation.
    - The C(--diff) option avoids to retrieve the entire configuration
      before and after the change has been applied for performance reasons.
      Instead this module will only retrieve all subtree, that are selected
      by the update, replace and delete parameters.
options:
  prefix:
    description:
      - Path prefix that is applied to all paths in that request
    type: str
  update:
    description:
      - List of path/value pairs to be updated (operation: merge)
    type: list
    element: dict
  relace:
    description:
      - List of path/value pairs to be updated (operation: replace)
    type: list
    element: dict
  delete:
    description:
      - List of paths to be deleted
    type: list
    element: dict
requirements:
  - grpcio
  - protobuf
"""

EXAMPLES = """
- name: Update Nodal Configuration (using gNMI SET)
  gnmi_config:
    prefix: configure
    update:
      - path: system/location
        val: Melbourne
      - path: system/contact
        val: nokia
    replace:
      - path: service/md-auto-id
        val:
          service-id-range:
            start: 10000
            end: 99999
          customer-id-range:
            start: 10000
            end: 10999
    delete:
      - system/cron
"""

RETURN = """
{
    "prefix": "configure",
    "response": [
        {
            "op": "DELETE",
            "path": "system/cron"
        },
        {
            "op": "REPLACE",
            "path": "service/md-auto-id"
        },
        {
            "op": "UPDATE",
            "path": "system/location"
        },
        {
            "op": "UPDATE",
            "path": "system/contact"
        }
    ],
    "timestamp": "2020-02-18T00:19:30.805600"
}
"""

from ansible.module_utils._text import to_text
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection, ConnectionError


def main():
    backup_spec = dict(filename=dict(), dir_path=dict(type="path"))
    argument_spec = dict(
        backup=dict(type="bool", default=False),
        backup_options=dict(type="dict", options=backup_spec),
        prefix=dict(type='str', required=False),
        update=dict(type='list', elements='dict', required=False),
        replace=dict(type='list', elements='dict', required=False),
        delete=dict(type='list', elements='str', required=False)
    )
    required_one_of = [["backup", "update", "replace", "delete"]]

    module = AnsibleModule(argument_spec=argument_spec,
                           required_one_of=required_one_of,
                           supports_check_mode=False)

    pathList = []
    if 'update' in module.params and module.params['update']:
        pathList.extend([update['path'] for update in module.params['update']])
    if 'replace' in module.params and module.params['replace']:
        pathList.extend([update['path'] for update in module.params['replace']])
    if 'delete' in module.params and module.params['delete']:
        pathList.extend(module.params['delete'])

    result = {}
    try:
        connection = Connection(module._socket_path)

        if pathList:
            # changes are contained: update, replace and/or delete
            if module.params["backup"]:
                snapshot1 = connection.gnmiGet(type='config', path=['/'])
            else:
                snapshot1 = connection.gnmiGet(type='config', prefix=module.params['prefix'], path=pathList)

            response = connection.gnmiSet(**module.params)

            if module.params["backup"]:
                snapshot2 = connection.gnmiGet(type='config', path=['/'])
            else:
                snapshot2 = connection.gnmiGet(type='config', prefix=module.params['prefix'], path=pathList)

            result['output'] = response

            if (snapshot1 != snapshot2):
                result['changed'] = True
                if module._diff:
                    result['diff'] = {'before': snapshot1, 'after': snapshot2}
                if module.params["backup"]:
                    result['__backup__'] = snapshot1
        elif module.params["backup"]:
            # backup only: take full config snapshot an return
            snapshot = connection.gnmiGet(type='config', path=['/'])
            result['__backup__'] = snapshot
        else:
            # Nothing to do: There are no updates and no backup requested
            pass

    except ConnectionError as exc:
        module.fail_json(msg=to_text(exc, errors='surrogate_then_replace'), code=exc.code)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
