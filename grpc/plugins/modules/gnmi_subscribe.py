# (c) 2020 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
---
module: gnmi_subscribe
author:
    - "Hans Thienpondt (@HansThienpondt)"
    - "Sven Wisotzky (@wisotzky)"
short_description: Subscription based retrieval of config/state information
description:
    - gRPC is a high performance, open-source universal RPC framework.
    - This module enables the user to receive configuration and/or state
      information from gNMI enabled devices using subscriptions.
    - Subscriptions of more POLL are NOT supported
    - The use of aliases is NOT supported
options:
  prefix:
    description:
      - Path prefix that is applied to all paths in that request
    type: str
    default: '/'
  subscription:
    description:
      - Set of subscriptions to create
    type: list
    elements: dict
    required: true
  mode:
    description:
      - Mode of subscription
    type: str
    choices: ['STREAM','ONCE']
    default: ONCE
  duration:
    description:
      - In mode STREAM to define on how long to monitor for periodic/on_change updates
      - In mode ONCE used to define the timeout to transmit subsequent updates
    type: int
    default: 20
  qos:
    description:
      - DSCP marking to be used
    type: int
  allow_aggregation:
    descrition:
      - Aggregate elements that are marked in the schema as eligable for aggregation
    type: bool
  updates_only:
    description:
      - Only transmit updates to the current state (mode must be STREAM)
      - If enabled, the initial state is not send to the client (just the sync message)
    type: bool
requirements:
  - grpcio
  - protobuf
"""

EXAMPLES = """
- name: Get Nodal Configuration (using gNMI Subscribe/ONCE)
  gnmi_subscribe:
    mode: ONCE
    subscription:
    - path: /configure

- name: gNMI streaming telemetry
  gnmi_subscribe:
    duration: 5
    prefix: /state
    mode: STREAM
    subscription:
    - path: /port[port-id=1/1/1]/ethernet/statistics
        mode: SAMPLE
        sampleInterval: 1000000000
    - path: /port[port-id=1/1/2]/ethernet/statistics
        mode: SAMPLE
        sampleInterval: 1000000000
"""

RETURN = """
[
    {
        "prefix": "/state/port[port-id=1/1/1]/ethernet/statistics",
        "timestamp": "2020-02-18T00:19:34.954275",
        "values": {
            "collisions": "0",
            "crc-align-errors": "0",
            "drop-events": "0",
            "fragments": "0",
            "in-broadcast-packets": "0",
            "in-errors": 0,
            "in-multicast-packets": "0",
            "in-octets": "0",
            "in-unicast-packets": "0",
            "in-utilization": 0,
            "jabbers": "0",
            "out-broadcast-packets": "0",
            "out-errors": 0,
            "out-multicast-packets": "0",
            "out-octets": "0",
            "out-unicast-packets": "0",
            "out-utilization": 0,
            "oversize-packets": "0",
            "total-broadcast-packets": "0",
            "total-multicast-packets": "0",
            "total-octets": "0",
            "total-packets": "0",
            "undersize-packets": "0"
        }
    },
    {
        "prefix": "/state/port[port-id=1/1/1]/ethernet/statistics/ethernet-like-medium",
        "timestamp": "2020-02-18T00:19:34.954320",
        "values": {
            "frame-too-long": "0"
        }
    },
    {
        "prefix": "/state/port[port-id=1/1/1]/ethernet/statistics/ethernet-like-medium/collision",
        "timestamp": "2020-02-18T00:19:34.954360",
        "values": {
            "excessive": "0",
            "late": "0",
            "multiple": "0",
            "single": "0"
        }
    },
    ...
]
"""
from ansible.module_utils._text import to_text
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection, ConnectionError


def main():
    argument_spec = dict(
        prefix=dict(type='str', default='/'),
        subscription=dict(type='list', required=True),
        mode=dict(type='str', default='ONCE', choices=['STREAM', 'ONCE']),
        duration=dict(type='int', default=20),
        qos=dict(type='int', required=False),
        allow_aggregation=dict(type='bool', required=False),
        updates_only=dict(type='bool', required=False)
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    connection = Connection(module._socket_path)

    try:
        response = connection.gnmiSubscribe(**module.params)
    except ConnectionError as exc:
        module.fail_json(msg=to_text(exc, errors='surrogate_then_replace'), code=exc.code)

    result = {}
    result['output'] = response
    result['changed'] = False

    module.exit_json(**result)


if __name__ == '__main__':
    main()
