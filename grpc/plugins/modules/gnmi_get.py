# (c) 2020 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
---
module: gnmi_get
author:
    - "Hans Thienpondt (@HansThienpondt)"
    - "Sven Wisotzky (@wisotzky)"
short_description: Retrieve config/state information from networking device
description:
    - gRPC is a high performance, open-source universal RPC framework.
    - This module enables the user to fetch configuration and/or state
      information from gNMI enabled devices.
options:
  type:
    description:
      - Type of data elements being requested
    type: str
    choices: ['ALL','CONFIG','STATE','OPERATIONAL']
    default: CONFIG
  prefix:
    description:
      - Path prefix that is applied to all paths in that request
    type: str
    default: '/'
  path:
    description:
      - Paths requested by the user
    type: list
    elements: str
    default: ['']
requirements:
  - grpcio
  - protobuf
"""

EXAMPLES = """
- name: Get Nodal Configuration
  gnmi_get:

- name: Get Nodal Configuration (Selective Branches)
  gnmi_get:
    type: CONFIG
    prefix: /configure
    path:
      - system/location
      - system/contact
      - service/md-auto-id
      - port[port-id=1/1/1]
"""

RETURN = """
"configure": {
    "port": [
        {
            "ethernet": {
                "mode": "access"
            },
            "port-id": "1/1/1"
        }
    ],
    "service": {
        "md-auto-id": {
            "customer-id-range": {
                "end": 10999,
                "start": 10000
            },
            "service-id-range": {
                "end": 99999,
                "start": 10000
            }
        }
    },
    "system": {
        "contact": "nokia",
        "location": "Melbourne"
    }
}
"""

from ansible.module_utils._text import to_text
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection, ConnectionError


def main():
    argument_spec = dict(
        type=dict(type='str', default='CONFIG', choices=['ALL', 'CONFIG', 'STATE', 'OPERATIONAL']),
        prefix=dict(type='str', default='/'),
        path=dict(type='list', elements='str', default=[''])
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    connection = Connection(module._socket_path)

    try:
        response = connection.gnmiGet(**module.params)
    except ConnectionError as exc:
        module.fail_json(msg=to_text(exc, errors='surrogate_then_replace'), code=exc.code)

    result = {}
    result['output'] = response
    result['changed'] = False

    module.exit_json(**result)


if __name__ == '__main__':
    main()
