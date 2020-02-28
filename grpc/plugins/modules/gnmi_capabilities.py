# (c) 2020 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: gnmi_capabilities
author:
    - "Hans Thienpondt (@HansThienpondt)"
    - "Sven Wisotzky (@wisotzky)"
short_description: Get gNMI server capabilities
description:
    - gRPC is a high performance, open-source universal RPC framework.
    - This module allows the user to retrieve the gNMI capabilities from
      a managed device
options:
requirements:
  - grpcio
  - protobuf
"""

EXAMPLES = """
- name: gNMI Capabilities
  gnmi_capabilities:
"""

RETURN = """
{
"gNMIVersion": "0.7.0",
"supportedEncodings": [
    "JSON",
    "BYTES"
],
"supportedModels": [
    {
        "name": "nokia-conf",
        "organization": "Nokia",
        "version": "19.10.B1-43"
    },
    {
        "name": "nokia-state",
        "organization": "Nokia",
        "version": "19.10.B1-43"
    },
    ...
]
"""

from ansible.module_utils._text import to_text
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection, ConnectionError


def main():
    argument_spec = dict()

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    try:
        connection = Connection(module._socket_path)
        response = connection.gnmiCapabilities()
    except ConnectionError as exc:
        module.fail_json(msg=to_text(exc, errors='surrogate_then_replace'), code=exc.code)

    result = {}
    result['output'] = module.from_json(response)
    result['changed'] = False

    module.exit_json(**result)


if __name__ == '__main__':
    main()
