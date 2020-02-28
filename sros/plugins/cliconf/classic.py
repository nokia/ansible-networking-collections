# (c) 2019 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
---
author: Nokia
cliconf: nokia.sros.classic
short_description: Cliconf plugin to configure and run CLI commands on Nokia SR OS devices (classic mode)
description:
  - This plugin provides low level abstraction APIs for sending CLI commands and
    receiving responses from Nokia SR OS network devices.
"""

import re
import json

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils.common._collections_compat import Mapping
from ansible.module_utils._text import to_text
from ansible.module_utils.network.common.utils import to_list
from ansible.plugins.cliconf import CliconfBase


class Cliconf(CliconfBase):

    def get_device_operations(self):
        return {                                    # supported: ---------------
            'supports_commit': True,                # identify if commit is supported by device or not
            'supports_rollback': True,              # identify if rollback is supported or not
            'supports_defaults': True,              # identify if fetching running config with default is supported
            'supports_onbox_diff': True,            # identify if on box diff capability is supported or not
                                                    # unsupported: -------------
            'supports_replace': False,              # no replace candidate >> running
            'supports_admin': False,                # no admin-mode
            'supports_multiline_delimiter': False,  # no multiline delimiter
            'supports_commit_label': False,         # no commit-label
            'supports_commit_comment': False,       # no commit-comment
            'supports_generate_diff': False,        # not supported
            'supports_diff_replace': False,         # not supported
            'supports_diff_match': False,           # not supported
            'supports_diff_ignore_lines': False     # not supported
        }

    def get_sros_rpc(self):
        return [
            'get_config',          # Retrieves the specified configuration from the device
            'edit_config',         # Loads the specified commands into the remote device
            'get_capabilities',    # Retrieves device information and supported rpc methods
            'get',                 # Execute specified command on remote device
            'get_default_flag'     # CLI option to include defaults for config dumps
        ]

    def get_option_values(self):
        return {
            'format': ['text'],
            'diff_match': [],
            'diff_replace': [],
            'output': ['text']
        }

    def get_device_info(self):
        device_info = dict()
        device_info['network_os'] = 'nokia.sros.classic'
        device_info['network_os_platform'] = 'Nokia 7x50'

        reply = self.get('show system information')
        data = to_text(reply, errors='surrogate_or_strict').strip()

        match = re.search(r'System Version\s+:\s+(.+)', data)
        if match:
            device_info['network_os_version'] = match.group(1)

        match = re.search(r'System Type\s+:\s+(.+)', data)
        if match:
            device_info['network_os_model'] = match.group(1)

        match = re.search(r'System Name\s+:\s+(.+)', data)
        if match:
            device_info['network_os_hostname'] = match.group(1)

        match = re.search(r'Configuration Mode Oper:\s+(.+)', data)
        if match:
            device_info['sros_config_mode'] = match.group(1)
        else:
            device_info['sros_config_mode'] = 'classic'

        return device_info

    def get_capabilities(self):
        capabilities = super(Cliconf, self).get_capabilities()
        capabilities['device_operations'] = self.get_device_operations()
        capabilities['rpc'] = self.get_sros_rpc()
        capabilities['device_info'] = self.get_device_info()
        capabilities['network_api'] = 'cliconf'
        capabilities.update(self.get_option_values())
        return json.dumps(capabilities)

    def get_default_flag(self):
        return ['detail']

    def is_classic_mode(self):
        reply = self.send_command('/show system information')
        data = to_text(reply, errors='surrogate_or_strict').strip()
        match = re.search(r'Configuration Mode Oper:\s+(.+)', data)
        return not match or match.group(1) == 'classic'

    def get_config(self, source='running', format='text', flags=None):
        if source != 'running':
            raise ValueError("fetching configuration from %s is not supported" % source)

        if format != 'text':
            raise ValueError("'format' value %s is invalid. Only format supported is 'text'" % format)

        if not self.is_classic_mode():
            raise ValueError("Nokia SROS node is not running in classic mode. Use ansible_network_os=nokia.sros.md")

        cmd = 'admin display-config %s' % ' '.join(flags)
        self.send_command('exit all')
        response = self.send_command(cmd.strip())
        pos1 = response.find('exit all')
        pos2 = response.rfind('exit all') + 8
        return response[pos1:pos2]

    def edit_config(self, candidate=None, commit=True, replace=None, comment=None):
        operations = self.get_device_operations()
        self.check_edit_config_capability(operations, candidate, commit, replace, comment)

        if not self.is_classic_mode():
            raise ValueError("Nokia SROS node is not running in classic mode. Use ansible_network_os=nokia.sros.md")

        requests = []
        responses = []

        try:
            self.send_command('exit all')
            for cmd in to_list(candidate):
                if isinstance(cmd, Mapping):
                    requests.append(cmd['command'])
                    responses.append(self.send_command(**cmd))
                else:
                    requests.append(cmd)
                    responses.append(self.send_command(cmd))

        except AnsibleConnectionFailure as exc:
            self.send_command('exit all')
            self.send_command('admin rollback revert latest-rb')
            raise exc

        self.send_command('exit all')
        rawdiffs = self.send_command('admin rollback compare')
        match = re.search(r'\r?\n-+\r?\n(.*)\r?\n-+\r?\n', rawdiffs, re.DOTALL)
        if match:
            if commit:
                self.send_command('admin rollback save')
            else:
                # Special hack! We load the config to running and rollback
                # to just figure out the delta. this might be risky in
                # check-mode, because it causes the changes contained to
                # become temporary active.

                self.send_command('admin rollback revert latest-rb')
            return {'request': requests, 'response': responses, 'diff': match.group(1)}
        else:
            return {'request': requests, 'response': responses}

    def get(self, command, prompt=None, answer=None, sendonly=False, output=None, newline=True, check_all=False):
        if output:
            raise ValueError("'output' value %s is not supported for get" % output)

        return self.send_command(command=command, prompt=prompt, answer=answer, sendonly=sendonly, newline=newline, check_all=check_all)

    def rollback(self, rollback_id, commit=True):
        if not self.is_classic_mode():
            raise ValueError("Nokia SROS node is not running in classic mode. Use ansible_network_os=nokia.sros.md")

        self.send_command('exit all')

        if str(rollback_id) == '0':
            rollback_id = 'latest-rb'

        rawdiffs = self.send_command('admin rollback compare {0} to active-cfg'.format(rollback_id))
        match = re.search(r'\r?\n-+\r?\n(.*)\r?\n-+\r?\n', rawdiffs, re.DOTALL)

        if match:
            if commit:
                # After executing the rollback another checkpoint is generated
                # This is required, to align running and latest-rb for follow-up requests
                self.send_command('admin rollback revert {0}'.format(rollback_id))
                self.send_command('admin rollback save')
            return {'diff': match.group(1).strip()}
        return {}
