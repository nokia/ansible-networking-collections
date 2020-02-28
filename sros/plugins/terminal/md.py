# (c) 2019 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
---
author: nokia
terminal: nokia.sros.md
short_description: MD-CLI terminal support for Nokia SR OS devices
"""

import re

from ansible.plugins.terminal import TerminalBase
from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils._text import to_text


class TerminalModule(TerminalBase):
    terminal_stdout_re = [
        re.compile(br"[\r\n]+\!?\*?(\((ex|gl|pr|ro)\))?\[.*\][\r\n]+[ABCD]\:\S+\@\S+\#\s"),
        re.compile(br"[\r\n]+\*?[ABCD]:[\w\-\.\>]+[#\$]\s")
    ]

    terminal_stderr_re = [
        re.compile(br"[\r\n]Error: .*[\r\n]+"),
        re.compile(br"[\r\n](MINOR|MAJOR|CRITICAL): .*[\r\n]+")
    ]

    def __init__(self, *args, **kwargs):
        super(TerminalModule, self).__init__(*args, **kwargs)

    def warning(self, msg):
        self._connection.queue_message('warning', msg)

    def on_open_shell(self):
        try:
            prompt = self._get_prompt().strip()
            if b'\n' in prompt:
                # node is running md-cli
                self._exec_cli_command(b'environment delete prompt')
                self._exec_cli_command(b'environment progress-indicator admin-state disable')
                self._exec_cli_command(b'environment more false')
                self._exec_cli_command(b'/!classic-cli')
                self._exec_cli_command(b'environment no more')
                self._exec_cli_command(b'/!md-cli')
            else:
                # node is running classic-cli
                self._exec_cli_command(b'environment no more')

        except AnsibleConnectionFailure:
            raise AnsibleConnectionFailure('unable to set terminal parameters')

        reply = self._exec_cli_command(b'show system information')
        data = to_text(reply, errors='surrogate_or_strict').strip()
        match = re.search(r'Configuration Mode Oper:\s+(.+)', data)
        if not match or match.group(1) == 'classic':
            host = self._connection.get_option('host')
            self.warning("%s is running in classic mode. Use: `ansible_network_os: nokia.sros.classic`" % host)
