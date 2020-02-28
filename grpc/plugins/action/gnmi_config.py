# (c) 2020 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.nokia.grpc.plugins.action.network import (
    ActionModule as ActionNetworkModule,
)


class ActionModule(ActionNetworkModule):
    def run(self, tmp=None, task_vars=None):
        del tmp  # tmp no longer has any effect

        self._config_module = True
        if self._play_context.connection.split(".")[-1] != "gnmi":
            return {
                "failed": True,
                "msg": "Connection type %s is not valid for gnmi_config module"
                % self._play_context.connection,
            }

        return super(ActionModule, self).run(task_vars=task_vars)
