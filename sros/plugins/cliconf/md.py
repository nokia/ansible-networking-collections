# (c) 2019 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
---
author: Nokia
cliconf: nokia.sros.md
short_description: Cliconf plugin to configure and run CLI commands on Nokia SR OS devices (model-driven mode)
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
            'supports_replace': True,               # identify if running config replace with candidate config is supported
                                                    # unsupported: -------------
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
            'get',                 # Execute specified command on remote device
            'get_capabilities',    # Retrieves device information and supported rpc methods
            'get_default_flag',    # CLI option to include defaults for config dumps
            'commit',              # Load configuration from candidate to running
            'discard_changes'      # Discard changes to candidate datastore
        ]

    def get_option_values(self):
        # format: json is supported from SROS19.10 onwards in MD MODE only
        return {
            'format': ['text', 'json'],
            'diff_match': [],
            'diff_replace': [],
            'output': ['text']
        }

    def get_device_info(self):
        device_info = dict()
        device_info['network_os'] = 'nokia.sros.md'
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

    def is_config_mode(self):
        """
        After a MD-CLI user has entered the edit-config command, the CLI
        session is in configuration mode. This is indicated by changing
        the MD-CLI context prompt (1st line) as following:

        (ex)[...] - exclusive mode (locked) for candidate configuration
        (gl)[...] - global (shared) mode for candidate configuration
        (pr)[...] - private mode for candidate configuration
        (ro)[...] - read-only mode

        Ansible does not expose different edit-config modes, while this
        plugin is using private mode to avoid interference with concurrent
        MD-CLI or NETCONF sessions.

        Note, that is Ansible module will use "edit-config private" and
        "quit-config" to enter and leave configuration mode. The
        alternative of using "configure private" is not supported.

        :return: True if session is running in configuration mode
        """

        prompt = self._connection.get_prompt().strip()
        return prompt.startswith(b'(')

    def is_classic_cli(self):
        """
        Determines if the session is running in Classic CLI or MD-CLI.
        Classic CLI uses a single line prompt while MD-CLI uses a multi
        line prompt. Setting is not static as it is possible to toggle
        between CLI engines:
          //             - toggle between modes
          /!md-cli       - set session to md-cli
          /!classic-cli  - set session to classic-cli

        It's also possible to execute single commands of the other
        engine by prepending the command with '//'.

        For integration purposes keep into consideration that MD mode
        and MD CLI are disabled by default. Please contact your Nokia
        SE/CE team to learn, if MD mode is supported on the platforms
        and releases used.

        :return: True if session is in classic CLI
        """

        prompt = self._connection.get_prompt().strip()
        return b'\n' not in prompt

    def enable_config_mode(self):
        if self.is_classic_cli():
            self.send_command('/!md-cli')

        self.send_command('exit all')

        if not self.is_config_mode():
            self.send_command('edit-config private')

    def is_classic_mode(self):
        reply = self.send_command('/show system information')
        data = to_text(reply, errors='surrogate_or_strict').strip()
        match = re.search(r'Configuration Mode Oper:\s+(.+)', data)
        return not match or match.group(1) == 'classic'

    def get_config(self, source='running', format='text', flags=None):
        if source not in ('startup', 'running', 'candidate'):
            raise ValueError("fetching configuration from %s is not supported" % source)

        if format not in self.get_option_values()['format']:
            raise ValueError("'format' value %s is invalid. Valid values are %s" % (format, ','.join(self.get_option_values()['format'])))

        if self.is_classic_mode():
            raise ValueError("Nokia SROS node is running in classic mode. Use ansible_network_os=nokia.sros.classic")

        if self.is_classic_cli():
            self.send_command('/!md-cli')

        if format == 'text':
            cmd = 'info %s %s' % (source, ' '.join(flags))
        else:
            cmd = 'info %s %s %s' % (source, format, ' '.join(flags))

        self.send_command('exit all')
        if self.is_config_mode():
            # This Ansible module always exists config-mode after any edit-config
            # MD-CLI operation. Therefore the code below should actually never be
            # executed.
            # If get_config() is called with source='candidate', it is somewhat
            # assumed that we are in config-mode, because in operational mode
            # there is no candidate (aka candidate=running).

            response = self.send_command(cmd.strip())
        else:
            # This Ansible plugin calls 'info' rather then 'admin show configuration'
            # because it provides additional options such as 'info detail' to include
            # default values. Also it would support alternative output formats (json).

            if source == 'startup':
                self.send_command('edit-config private')
                self.send_command('configure')
                self.send_command('rollback startup')
                self.send_command('exit all')
                response = self.send_command(cmd.strip())
                self.send_command('discard')
            else:
                self.send_command('edit-config read-only')
                response = self.send_command(cmd.strip())
            self.send_command('quit-config')

        return response

    def edit_config(self, candidate=None, commit=True, replace=None, comment=None):
        operations = self.get_device_operations()
        self.check_edit_config_capability(operations, candidate, commit, replace, comment)

        if self.is_classic_mode():
            raise ValueError("Nokia SROS node is running in classic mode. Use ansible_network_os=nokia.sros.classic")

        self.enable_config_mode()

        requests = []
        responses = []

        try:
            if replace:
                if candidate:
                    cmd = 'delete configure'
                else:
                    cmd = 'load full-replace {0}'.format(replace).strip()
                requests.append(cmd)
                responses.append(self.send_command(cmd))

            for cmd in to_list(candidate):
                if isinstance(cmd, Mapping):
                    requests.append(cmd['command'])
                    responses.append(self.send_command(**cmd))
                else:
                    requests.append(cmd)
                    responses.append(self.send_command(cmd))

        except AnsibleConnectionFailure as exc:
            self.send_command('exit all')
            self.send_command('discard')
            self.send_command('quit-config')
            raise exc

        self.send_command('exit all')
        diffs = self.send_command('compare').strip()
        if diffs:
            if commit:
                self.send_command('commit')
                self.send_command('quit-config')
            else:
                self.send_command('validate')
                self.send_command('discard')
                self.send_command('quit-config')
            return {'request': requests, 'response': responses, 'diff': diffs}
        else:
            return {'request': requests, 'response': responses}

    def get(self, command, prompt=None, answer=None, sendonly=False, output=None, newline=True, check_all=False):
        if output:
            raise ValueError("'output' value %s is not supported for get" % output)

        return self.send_command(command=command, prompt=prompt, answer=answer, sendonly=sendonly, newline=newline, check_all=check_all)

    def rollback(self, rollback_id, commit=True):
        if self.is_classic_mode():
            raise ValueError("Nokia SROS node is running in classic mode. Use ansible_network_os=nokia.sros.classic")

        self.enable_config_mode()

        self.send_command('configure')
        self.send_command('rollback {0}'.format(rollback_id).strip())
        self.send_command('exit all')
        diffs = self.send_command('compare').strip()
        if diffs:
            if commit:
                self.send_command('commit')
                self.send_command('quit-config')
            else:
                self.send_command('discard')
                self.send_command('quit-config')
            return {'diff': diffs.strip()}
        else:
            return {}

    def commit(self):
        if self.is_classic_cli():
            self.send_command('/!md-cli')

        if self.is_config_mode():
            self.send_command('commit')
            self.send_command('quit-config')

    def discard_changes(self):
        if self.is_classic_cli():
            self.send_command('/!md-cli')

        if self.is_config_mode():
            self.send_command('discard')
            self.send_command('quit-config')
