![NOKIA](Logo_Nokia.png)
# Ansible Collection - nokia.sros

***

This [collection](https://galaxy.ansible.com/nokia/sros) is to provide automation for Nokia SR OS devices using Ansible by RedHat.

## Installation
Distribution is via [ansible-galaxy](https://galaxy.ansible.com/).

Make sure you have the Ansible [netcommon](https://galaxy.ansible.com/ansible/netcommon) collection installed:
```bash
ansible-galaxy collection install ansible.netcommon
```

To install this collection, please use the following command:
```bash
ansible-galaxy collection install nokia.sros
```

If you have already installed a previous version, you can  upgrade to the latest version of this collection, by adding the `--force-with-deps` option:
```bash
ansible-galaxy collection install nokia.sros --force-with-deps
```

## Usage
To use this collection make sure to set `ansible_network_os=nokia.sros.{mode}` in your host inventory.

## Requirements
* Ansible 2.9 or newer

## Supported Nokia SR OS versions
Tested with SR OS 19.5, 19.7 and 19.10

## Playbooks
### Classic CLI
* [sros_classic_cli_command_demo.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_classic_cli_command_demo.yml)
* [sros_classic_cli_config_demo.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_classic_cli_config_demo.yml)
* [sros_classic_cli_backup_restore_demo.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_classic_cli_backup_restore_demo.yml)
### MD-CLI
* [sros_mdcli_command_demo.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_mdcli_command_demo.yml)
* [sros_mdcli_config_demo.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_mdcli_config_demo.yml)
* [sros_mdcli_backup_restore_demo.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_mdcli_backup_restore_demo.yml)
### NETCONF
* [sros_nc_state_demo.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_nc_state_demo.yml)
### Device information
* [sros_cli_device_info.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_cli_device_info.yml)
* [sros_nc_device_info.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_nc_device_info.yml)

## Modules
The Ansible module `device_info` returns information about the networking device connected. This module is designed to work with CLI and NETCONF connections.
Example result:
```yaml
  output:
    network_os: "nokia.sros.classic"
    network_os_hostname: "Antwerp"
    network_os_model: "7750 SR-12"
    network_os_platform: "Nokia 7x50"
    network_os_version: "B-19.5.R2"
    sros_config_mode: "classic"
```

## Roles
None

## Plugins
|     Network OS      | terminal | cliconf | netconf |
|---------------------|:--------:|:-------:|:-------:|
| nokia.sros.md       |     Y    |    Y    |    Y    |
| nokia.sros.classic  |     Y    |    Y    |    -    |
| nokia.sros.light    |     Y    |    Y    |    -    |


### CLASSIC MODE
In the case of classic CLI we are relying on the built-in rollback feature.
Therefore it is required that the rollback location is properly configured.
For example:
```
     A:Antwerp# file md cf3:/rollbacks
     *A:Antwerp# configure system rollback rollback-location cf3:/rollbacks/config
     INFO: CLI No checkpoints currently exist at the rollback location.
     *A:Antwerp# admin rollback save
     Saving rollback configuration to cf3:/rollbacks/config.rb... OK
     *A:Antwerp#
```

This Ansible collection also contains a playbook, on how to enable rollbacks:
[sros_classic_cli_commission.yml](https://raw.githubusercontent.com/nokia/ansible-networking-collections/master/sros/playbooks/sros_classic_cli_commission.yml).

Note: Use `nokia.sros.light` for SR OS nodes that don't support rollback or if the use of the
rollback is not desired.


Snapshot/rollback is used the following way:
* A new temporary rollback checkpoint is created at the beginning of every
  cli_config operation.
* If a configuration request runs into an error, the configuration is restored
  by rolling back to the checkpoint that was created before. This actually
  translates to a rollback-on-error behavior.
* If the configuration request is successful, the new running configuration is
  compared against the previous checkpoint using the underlying nodal feature.
  This is needed to provide the `change` indicator, but also to provide the
  actual differences, if the `--diff` option is used.
* If operator requests to do a dry-run by providing the `--check` option,
  the change is executed against the running config and reverted to the
  checkpoint straight away. Following that approach, syntax and
  semantic checks will be executed - but also we get `change` indication
  including the list of differences, if `--diff` option was provided.
* At the end of the cli_config operation the checkpoint created will be
  deleted to keep a clean rollback history.

WARNING:
* Be aware, that dry-run is implemented as temporary activation of the
  new configuration with immediate rollback. Users need to consider potential
  service impact because of this.
* Rollback-on-error might have side-effects based on the way SR OS has implemented
  the checkpoint/rollback feature. In its operation for impacted modules (such
  as BGP within VPRN) it reverts to default configuration (e.g. shutdown) prior
  to the execution of commands to revert the checkpoint's configuration. Please
  check the `Basic System Config Guide` for more information.

RESTRICTIONS:
* Some platforms might not support checkpoint/rollback
* Changes are always written directly to running
* Operation `replace` is currently not supported
* The oldest rollback checkpoint is removed after plugin operation.


### LIGHT MODE
The use of `nokia.sros.classic` depends on the nodal rollback feature and comes with
a set of side-effects as discussed before. In cases where the rollback feature is not
supported, for example when using older SR OS releases, or if the use of the rollback
is not desired `nokia.sros.light` should be used.

The plugin relies
on the prompt change indicator to determine, if there was a change made by cli_config.
If a change causes asterisk to appear before prompt, then the task is considered as changed.

RESTRICTIONS:
* If there were unsaved changes on a device before running cli_conifg task it will be assumed as changed.
* This plugin does support neither `--diff` mode nor `--check` mode.


### MD MODE
To have the NETCONF plugin working, PR [#65718](https://github.com/ansible/ansible/pull/65718) has been integrated into `ansible:devel`. So the change should become active as part of the next Ansible release, which is Ansible 2.10.

PR [#65991](https://github.com/ansible/ansible/pull/65991) is tracking the backporting of this fix into Ansible 2.9.
