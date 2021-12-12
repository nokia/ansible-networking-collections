# (c) 2020 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
---
author:
  - "Hans Thienpondt (@HansThienpondt)"
  - "Sven Wisotzky (@wisotzky)"
connection: gnmi
short_description: Provides a persistent gRPC connection for gNMI API service
description:
  - This gRPC plugin provides methods to interact with the gNMI service.
  - OpenConfig gNMI specification
    https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md
  - gNMI API
    https://raw.githubusercontent.com/openconfig/gnmi/master/proto/gnmi/gnmi.proto
  - This connection plugin provides a persistent communication channel to
    remote devices using gRPC including the underlying transport (TLS).
  - The plugin binds to the gNMI gRPC service. It provide wrappers for gNMI
    requests (Capabilities, Get, Set, Subscribe)
requirements:
  - grpcio
  - protobuf
options:
  host:
    description:
      - Target host FQDN or IP address to establish gRPC connection.
    default: inventory_hostname
    vars:
      - name: ansible_host
  port:
    type: int
    description:
      - Specifies the port on the remote device that listens for connections
        when establishing the gRPC connection. If None only the C(host) part
        will be used.
    ini:
      - section: defaults
        key: remote_port
    env:
      - name: ANSIBLE_REMOTE_PORT
    vars:
      - name: ansible_port
  remote_user:
    description:
      - The username used to authenticate to the remote device when the gRPC
        connection is first established.  If the remote_user is not specified,
        the connection will use the username of the logged in user.
      - Can be configured from the CLI via the C(--user) or C(-u) options.
    ini:
      - section: defaults
        key: remote_user
    env:
      - name: ANSIBLE_REMOTE_USER
    vars:
      - name: ansible_user
  password:
    description:
      - Configures the user password used to authenticate to the remote device
        when first establishing the gRPC connection.
    vars:
      - name: ansible_password
      - name: ansible_ssh_pass
  private_key_file:
    description:
      - The PEM encoded private key file used to authenticate to the
        remote device when first establishing the grpc connection.
    ini:
      - section: grpc_connection
        key: private_key_file
    env:
      - name: ANSIBLE_PRIVATE_KEY_FILE
    vars:
      - name: ansible_private_key_file
  root_certificates_file:
    description:
      - The PEM encoded root certificate file used to create a SSL-enabled
        channel, if the value is None it reads the root certificates from
        a default location chosen by gRPC at runtime.
    ini:
      - section: grpc_connection
        key: root_certificates_file
    env:
      - name: ANSIBLE_ROOT_CERTIFICATES_FILE
    vars:
      - name: ansible_root_certificates_file
  certificate_chain_file:
    description:
      - The PEM encoded certificate chain file used to create a SSL-enabled
        channel. If the value is None, no certificate chain is used.
    ini:
      - section: grpc_connection
        key: certificate_chain_file
    env:
      - name: ANSIBLE_CERTIFICATE_CHAIN_FILE
    vars:
      - name: ansible_certificate_chain_file
  certificate_path:
    description:
      - Folder to search for certificate and key files
    ini:
      - section: grpc_connection
        key: certificate_path
    env:
      - name: ANSIBLE_CERTIFICATE_PATH
    vars:
      - name: ansible_certificate_path
  gnmi_encoding:
    description:
      - Encoding used for gNMI communication
      - Must be either JSON or JSON_IETF
      - If not provided, will run CapabilityRequest for auto-detection
    ini:
      - section: grpc_connection
        key: gnmi_encoding
    env:
      - name: ANSIBLE_GNMI_ENCODING
    vars:
      - name: ansible_gnmi_encoding
  grpc_channel_options:
    description:
      - Key/Value pairs (dict) to define gRPC channel options to be used
      - gRPC reference
        U(https://grpc.github.io/grpc/core/group__grpc__arg__keys.html)
      - Provide the I(ssl_target_name_override) option to override the TLS
        subject or subjectAltName (only in the case secure connections are
        used). The option must be provided in cases, when the FQDN or IPv4
        address that is used to connect to the device is different from the
        subject name that is provided in the host certificate. This is
        needed, because the TLS validates hostname or IP address to avoid
        man-in-the-middle attacks.
    vars:
      - name: ansible_grpc_channel_options
  grpc_environment:
    description:
      - Key/Value pairs (dict) to define environment settings specific to gRPC
      - The standard mechanism to provide/set the environment in Ansible
        cannot be used, because those environment settings are not passed to
        the client process that establishes the gRPC connection.
      - Set C(GRPC_VERBOSITY) and C(GRPC_TRACE) to setup gRPC logging. Need to
        add code for log forwarding of gRPC related log messages to the
        persistent messages log (see below).
      - Set C(HTTPS_PROXY) to specify your proxy settings (if needed).
      - Set C(GRPC_SSL_CIPHER_SUITES) in case the default TLS ciphers do not match
        what is offered by the gRPC server.
    vars:
      - name: ansible_grpc_environment
  persistent_connect_timeout:
    type: int
    description:
      - Configures, in seconds, the amount of time to wait when trying to
        initially establish a persistent connection. If this value expires
        before the connection to the remote device is completed, the connection
        will fail.
    default: 5
    ini:
      - section: persistent_connection
        key: connect_timeout
    env:
      - name: ANSIBLE_PERSISTENT_CONNECT_TIMEOUT
    vars:
      - name: ansible_connect_timeout
  persistent_command_timeout:
    type: int
    description:
      - Configures the default timeout value (in seconds) when awaiting a
        response after issuing a call to a RPC. If the RPC does not return
        before the timeout exceed, an error is generated and the connection
        is closed.
    default: 300
    ini:
      - section: persistent_connection
        key: command_timeout
    env:
      - name: ANSIBLE_PERSISTENT_COMMAND_TIMEOUT
    vars:
      - name: ansible_command_timeout
  persistent_log_messages:
    type: boolean
    description:
      - This flag will enable logging the command executed and response received
        from target device in the ansible log file. For this option to work the
        'log_path' ansible configuration option is required to be set to a file
        path with write access.
      - Be sure to fully understand the security implications of enabling this
        option as it could create a security vulnerability by logging sensitive
        information in log file.
    default: False
    ini:
      - section: persistent_connection
        key: log_messages
    env:
      - name: ANSIBLE_PERSISTENT_LOG_MESSAGES
    vars:
      - name: ansible_persistent_log_messages
"""

import os
import re
import json
import base64
import datetime

try:
    import grpc
    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False

try:
    from google import protobuf
    HAS_PROTOBUF = True
except ImportError:
    HAS_PROTOBUF = False

from ansible.errors import AnsibleConnectionFailure, AnsibleError
from ansible.plugins.connection import NetworkConnectionBase
from ansible.plugins.connection import ensure_connect

from google.protobuf import json_format
from ansible_collections.nokia.grpc.plugins.connection.pb import gnmi_pb2
from ansible.module_utils._text import to_text


class Connection(NetworkConnectionBase):
    """
    Connection plugin for gRPC

    To use gRPC connections in Ansible one (or more) sub-plugin(s) for the
    required gRPC service(s) must be loaded. To load gRPC sub-plugins use the
    method `register_service()` with the name of the sub-plugin to be
    registered.

    After loading the sub-plugin, Ansible modules can call methods provided by
    that sub-plugin. There is a wrapper available that consumes the attribute
    name {sub-plugin name}__{method name} to call a specific method of that
    sub-plugin.
    """

    transport = "nokia.grpc.gnmi"
    has_pipelining = True

    def __init__(self, play_context, new_stdin, *args, **kwargs):
        super(Connection, self).__init__(
            play_context, new_stdin, *args, **kwargs
        )

        self._task_uuid = to_text(kwargs.get("task_uuid", ""))

        if not HAS_PROTOBUF:
            raise AnsibleError(
                "protobuf is required to use gRPC connection type. " +
                "Please run 'pip install protobuf'"
            )
        if not HAS_GRPC:
            raise AnsibleError(
                "grpcio is required to use gRPC connection type. " +
                "Please run 'pip install grpcio'"
            )

        self._connected = False

    def readFile(self, optionName):
        """
        Reads a binary certificate/key file

        Parameters:
            optionName(str): used to read filename from options

        Returns:
            File content

        Raises:
            AnsibleConnectionFailure: file does not exist or read excpetions
        """
        path = self.get_option('certificate_path')
        if not path:
            path = '/etc/ssl:/etc/ssl/certs:/etc/ca-certificates'

        filename = self.get_option(optionName)
        if filename:
            if filename.startswith('~'):
                filename = os.path.expanduser(filename)
            if not filename.startswith('/'):
                for entry in path.split(':'):
                    if os.path.isfile(os.path.join(entry, filename)):
                        filename = os.path.join(entry, filename)
                        break
            if os.path.isfile(filename):
                try:
                    with open(filename, 'rb') as f:
                        return f.read()
                except Exception as exc:
                    raise AnsibleConnectionFailure(
                        'Failed to read cert/keys file %s: %s' % (filename, exc)
                    )
            else:
                raise AnsibleConnectionFailure(
                        'Cert/keys file %s does not exist' % filename
                    )
        return None

    def _connect(self):
        """
        Establish gRPC connection to remote node and create gNMI stub.

        This method will establish the persistent gRPC connection, if not
        already done. After this, the gNMI stub will be created. To get
        visibility about gNMI capabilities of the remote device, a gNM
        CapabilityRequest will be sent and result will be persisted.

        Parameters:
            None

        Returns:
            None
        """

        if self.connected:
            self.queue_message('v', 'gRPC connection to host %s already exist' % self._target)
            return

        grpcEnv = self.get_option('grpc_environment') or {}
        if not isinstance(grpcEnv, dict):
            raise AnsibleConnectionFailure("grpc_environment must be a dict")

        for key in grpcEnv:
            if grpcEnv[key]:
                os.environ[key] = str(grpcEnv[key])
            else:
                try:
                    del os.environ[key]
                except KeyError:
                    # no such setting in current environment, but thats ok
                    pass

        self._login_credentials = [
            ('username', self.get_option('remote_user')),
            ('password', self.get_option('password'))
        ]

        host = self.get_option('host')
        port = self.get_option('port')
        self._target = host if port is None else '%s:%d' % (host, port)
        self._timeout = self.get_option('persistent_command_timeout')

        certs = {}
        certs['root_certificates'] = self.readFile('root_certificates_file')
        certs['certificate_chain'] = self.readFile('certificate_chain_file')
        certs['private_key'] = self.readFile('private_key_file')

        options = self.get_option('grpc_channel_options')
        if options:
            if not isinstance(options, dict):
                raise AnsibleConnectionFailure("grpc_channel_options must be a dict")
            options = options.items()

        if certs['root_certificates'] or certs['private_key'] or certs['certificate_chain']:
            self.queue_message('v', 'Starting secure gRPC connection')
            creds = grpc.ssl_channel_credentials(**certs)
            self._channel = grpc.secure_channel(self._target, creds, options=options)
        else:
            self.queue_message('v', 'Starting insecure gRPC connection')
            self._channel = grpc.insecure_channel(self._target, options=options)

        self.queue_message('v', "gRPC connection established for user %s to %s" %
                           (self.get_option('remote_user'), self._target))

        self.queue_message('v', 'Creating gNMI stub')
        self._stub = gnmi_pb2.gNMIStub(self._channel)

        self._encoding = self.get_option('gnmi_encoding')
        if not self._encoding:
            self.queue_message('v', 'Run CapabilityRequest()')
            request = gnmi_pb2.CapabilityRequest()
            response = self._stub.Capabilities(request, metadata=self._login_credentials)
            self.queue_message('v', 'CapabilityRequest() succeeded')

            self._gnmiVersion = response.gNMI_version
            self._yangModels = response.supported_models

            if gnmi_pb2.Encoding.Value('JSON_IETF') in response.supported_encodings:
                self._encoding = 'JSON_IETF'
            elif gnmi_pb2.Encoding.Value('JSON') in response.supported_encodings:
                self._encoding = 'JSON'
            else:
                raise AnsibleConnectionFailure("No compatible supported encoding found (JSON or JSON_IETF)")
        else:
            if self._encoding not in ['JSON_IETF', 'JSON']:
                raise AnsibleConnectionFailure("Incompatible encoding '%s' requested (JSON or JSON_IETF)" % self._encoding)

        self._encoding_value = gnmi_pb2.Encoding.Value(self._encoding)

        self._connected = True
        self.queue_message('v', 'gRPC/gNMI connection has established successfully')

    def close(self):
        """
        Closes the active gRPC connection to the target host

        Parameters:
            None

        Returns:
            None
        """

        if self._connected:
            self.queue_message('v', "Closing gRPC connection to target host")
            self._channel.close()
        super(Connection, self).close()

    # -----------------------------------------------------------------------

    def _encodeXpath(self, xpath='/'):
        """
        Encodes XPATH to dict representation that allows conversion to gnmi_pb.Path object

        Parameters:
            xpath (str): path string using XPATH syntax

        Returns:
            (dict): path dict using gnmi_pb2.Path structure for easy conversion
        """
        mypath = []
        xpath = xpath.strip('\t\n\r /')
        if xpath:
            path_elements = re.split('''/(?=(?:[^\[\]]|\[[^\[\]]+\])*$)''', xpath)
            origin = {} # Optional namespace element, used for openconfig
            for e in path_elements:

                # Support namespaces with 'origin', required for openconfig
                ns = e.split(":")
                if len(ns)==2:
                    origin['origin'] = ns[0]
                    e = ns[1]
                elif len(ns)>2:
                    raise AnsibleConnectionFailure(f"Invalid path syntax: {e}")
                entry = {'name': e.split("[", 1)[0]}
                eKeys = re.findall('\[(.*?)\]', e)
                dKeys = dict(x.split('=', 1) for x in eKeys)
                if dKeys:
                    entry['key'] = dKeys
                mypath.append(entry)
            return {'elem': mypath, **origin}
        return {}

    def _decodeXpath(self, path):
        """
        Decodes XPATH from dict representation converted from gnmi_pb.Path object

        Parameters:
            path (dict): decoded gnmi_pb2.Path object

        Returns:
            (str): path string using XPATH syntax
        """
        result = []
        if 'elem' not in path:
            return ""
        for elem in path['elem']:
            tmp = elem['name']
            if 'key' in elem:
                for k, v in elem['key'].items():
                    tmp += "[%s=%s]" % (k, v)
            result.append(tmp)
        return '/'.join(result)

    def _encodeVal(self, data):
        """
        Encodes value to dict representation that allows conversion to gnmi_pb.TypedValue object

        Parameters:
            data (ANY): data to be encoded as gnmi_pb.TypedValue object

        Returns:
            (dict): dict using gnmi_pb.TypedValue structure for easy conversion
        """
        value = base64.b64encode(json.dumps(data).encode())
        if self._encoding == 'JSON_IETF':
            return {'jsonIetfVal': value}
        else:
            return {'jsonVal': value}

    def _decodeVal(self, val):
        """
        Decodes value from dict representation converted from gnmi_pb.TypedValue object

        Parameters:
            val (dict): decoded gnmi_pb.TypedValue object

        Returns:
            (ANY): extracted data
        """
        if 'jsonIetfVal' in val:
            return json.loads(base64.b64decode(val['jsonIetfVal']))
        elif 'jsonVal' in val:
            return json.loads(base64.b64decode(val['jsonVal']))
        else:
            raise AnsibleConnectionFailure("Ansible gNMI plugin does not support encoding for value: %s" % json.dumps(val))

    def _dictToList(self, aDict):
        for key in list(aDict):
            if key.startswith('___'):
                aDict[key[3:]] = [self._dictToList(val) if isinstance(val, dict) else val for val in aDict[key].values()]
                del aDict[key]
            else:
                if isinstance(aDict[key], dict):
                    aDict[key] = self._dictToList(aDict[key])
        return aDict

    def _mergeToSingleDict(self, rawData):
        result = {}

        for entry in rawData:
            if 'syncResponse' in entry and entry['syncResponse']:
                # Ignore: SyncResponse is sent after initial update
                break
            elif 'update' not in entry:
                # Ignore: entry without updates
                break
            elif 'timestamp' not in entry:
                # Subscribe response, enter update context
                entry = entry['update']
            else:
                # Get response, keep context
                pass

            prfx = result
            if ('prefix' in entry) and ('elem' in entry['prefix']):
                prfx_elements = entry['prefix']['elem']
            else:
                prfx_elements = []

            for elem in prfx_elements:
                eleName = elem['name']
                if 'key' in elem:
                    eleKey = json.dumps(elem['key'])
                    eleName = '___'+eleName
                    # Path Element has key => must be list()
                    if eleName in prfx:
                        # Path Element exists => Change Context
                        prfx = prfx[eleName]
                        if eleKey not in prfx:
                            # List entry does not exist => Create
                            prfx[eleKey] = elem['key']
                        prfx = prfx[eleKey]
                    else:
                        # Path Element does not exist => Create
                        prfx[eleName] = {}
                        prfx = prfx[eleName]
                        prfx[eleKey] = elem['key']
                        prfx = prfx[eleKey]
                else:
                    # Path Element hasn't key => must be dict()
                    if eleName in prfx:
                        # Path Element exists => Change Context
                        prfx = prfx[eleName]
                    else:
                        # Path Element does not exist => Create
                        prfx[eleName] = {}
                        prfx = prfx[eleName]

            for _upd in entry['update']:
                if 'val' not in _upd:
                    # requested path without content (no value) => skip
                    continue
                elif ('path' in _upd) and ('elem' in _upd['path']):
                    path_elements = _upd['path']['elem']
                    cPath = prfx
                elif prfx_elements:
                    path_elements = prfx_elements
                    cPath = result
                else:
                    # No path at all, replace the objecttree with value
                    result = self._decodeVal(_upd['val'])
                    prfx = result
                    continue

                # If path_elements has more than just a single entry,
                # we need to create/navigate to the specified subcontext
                for elem in path_elements[:-1]:
                    eleName = elem['name']
                    if 'key' in elem:
                        eleKey = json.dumps(elem['key'])
                        eleName = '___'+eleName
                        # Path Element has key => must be list()
                        if eleName in cPath:
                            # Path Element exists => Change Context
                            cPath = cPath[eleName]
                            if eleKey not in cPath:
                                # List entry does not exist => Create
                                cPath[eleKey] = elem['key']
                            cPath = cPath[eleKey]
                        else:
                            # Path Element does not exist => Create
                            cPath[eleName] = {}
                            cPath = cPath[eleName]
                            cPath[eleKey] = elem['key']
                            cPath = cPath[eleKey]
                    else:
                        # Path Element hasn't key => must be dict()
                        if eleName in cPath:
                            # Path Element exists => Change Context
                            cPath = cPath[eleName]
                        else:
                            # Path Element does not exist => Create
                            cPath[eleName] = {}
                            cPath = cPath[eleName]

                # The last entry of path_elements is the leaf element
                # that needs to be created/updated
                leaf_elem = path_elements[-1]
                if 'key' in leaf_elem:
                    eleKey = json.dumps(leaf_elem['key'])
                    eleName = '___'+leaf_elem['name']
                    if eleName not in cPath:
                        cPath[eleName] = {}
                    cPath = cPath[eleName]
                    cPath[eleKey] = self._decodeVal(_upd['val'])
                else:
                    cPath[leaf_elem['name']] = self._decodeVal(_upd['val'])

        return self._dictToList(result)

    def _simplifyUpdates(self, rawData):
        for msg in rawData:
            entry = json_format.MessageToDict(msg)
            if 'syncResponse' in entry:
                # Ignore: SyncResponse is sent after initial update
                pass
            elif 'update' in entry:
                result = {}
                update = entry['update']
                if 'prefix' in update:
                    result['prefix'] = '/'+self._decodeXpath(update['prefix'])
                if 'timestamp' in update:
                    result['timestamp'] = datetime.datetime.fromtimestamp(float(update['timestamp'])/1000000000).isoformat()
                if 'update' in update:
                    result['values'] = {self._decodeXpath(u['path']): self._decodeVal(u['val']) for u in update['update']}
                yield result
            else:
                # Ignore: Invalid message format
                pass

    # -----------------------------------------------------------------------
    @ensure_connect
    def gnmiCapabilities(self):
        """
        Executes a gNMI Capabilities request

        Parameters:
            None

        Returns:
            str: gNMI capabilities converted into JSON format
        """
        request = gnmi_pb2.CapabilityRequest()
        auth = self._login_credentials

        try:
            response = self._stub.Capabilities(request, metadata=auth)
        except grpc.RpcError as e:
            raise AnsibleConnectionFailure("%s" % e)
        return json_format.MessageToJson(response)

    @ensure_connect
    def gnmiGet(self, *args, **kwargs):
        """
        Executes a gNMI Get request

        Encoding that is used for data serialization is automatically determined
        based on the remote device capabilities. This gNMI plugin has implemented
        suppport for JSON_IETF (preferred) and JSON (fallback).

        Parameters:
            type (str): Type of data that is requested: ALL, CONFIG, STATE
            prefix (str): Path prefix that is added to all paths (XPATH syntax)
            paths (list): List of paths (str) to be captured

        Returns:
            str: GetResponse message converted into JSON format
        """
        # Remove all input parameters from kwargs that are not set
        input = dict(filter(lambda x: x[1], kwargs.items()))

        # Adjust input parameters to match specification for gNMI SetRequest
        if 'prefix' in input:
            input['prefix'] = self._encodeXpath(input['prefix'])
        if 'path' in input:
            input['path'] = [self._encodeXpath(path) for path in input['path']]
        if 'type' in input:
            input['type'] = input['type'].upper()
        input['encoding'] = self._encoding_value

        request = json_format.ParseDict(input, gnmi_pb2.GetRequest())
        auth = self._login_credentials

        try:
            response = self._stub.Get(request, metadata=auth)
        except grpc.RpcError as e:
            raise AnsibleConnectionFailure("%s" % e)

        output = self._mergeToSingleDict(json_format.MessageToDict(response)['notification'])
        return json.dumps(output, indent=4).encode()

    @ensure_connect
    def gnmiSet(self, *args, **kwargs):
        """
        Executes a gNMI Set request

        Encoding that is used for data serialization is automatically determined
        based on the remote device capabilities. This gNMI plugin has implemented
        suppport for JSON_IETF (preferred) and JSON (fallback).

        Parameters:
            prefix (str): Path prefix that is added to all paths (XPATH syntax)
            update (list): Path/Value pairs to be updated
            replace (list): Path/Value pairs to be replaced
            delete (list): Paths (str) to be deleted

        Returns:
            str: SetResponse message converted into JSON format
        """
        # Remove all input parameters from kwargs that are not set
        input = dict(filter(lambda x: x[1], kwargs.items()))

        # Backup options are not to be used in gNMI SetRequest
        if 'backup' in input:
            del input['backup']
        if 'backup_options' in input:
            del input['backup_options']

        # Adjust input parameters to match specification for gNMI SetRequest
        if 'prefix' in input:
            input['prefix'] = self._encodeXpath(input['prefix'])

        if 'delete' in input:
            input['delete'] = [self._encodeXpath(entry) for entry in input['delete']]

        if 'update' in input:
            for entry in input['update']:
                entry['path'] = self._encodeXpath(entry['path'])
                entry['val'] = self._encodeVal(entry['val'])

        if 'replace' in input:
            for entry in input['replace']:
                entry['path'] = self._encodeXpath(entry['path'])
                entry['val'] = self._encodeVal(entry['val'])

        request = json_format.ParseDict(input, gnmi_pb2.SetRequest())
        auth = self._login_credentials

        try:
            response = self._stub.Set(request, metadata=auth)
        except grpc.RpcError as e:
            raise AnsibleConnectionFailure("%s" % e)

        output = json_format.MessageToDict(response)
        output['timestamp'] = datetime.datetime.fromtimestamp(float(output['timestamp'])/1000000000).isoformat()
        if 'prefix' in output:
            output['prefix'] = self._decodeXpath(output['prefix'])
        for item in output['response']:
            item['path'] = self._decodeXpath(item['path'])

        return json.dumps(output, indent=4).encode()

    @ensure_connect
    def gnmiSubscribe(self, *args, **kwargs):
        """
        Executes a gNMI Subscribe request

        Encoding that is used for data serialization is automatically determined
        based on the remote device capabilities. This gNMI plugin has implemented
        suppport for JSON_IETF (preferred) and JSON (fallback).

        Parameters:
            prefix (str): Path prefix that is added to all paths (XPATH syntax)
            mode (str): Mode of subscription (STREAM, ONCE)
            subscription (list of dict): Subscription specification (path, interval, submode)
            duration (int): timeout, to stop receiving
            qos (int):  DSCP marking that is used
            updates_only (bool): Send only updates to initial state
            allow_aggregation (bool): Aggregate elements marked as eligible for aggregation

        Returns:
            str: Updates received converted into JSON format
        """
        # Remove all input parameters from kwargs that are not set
        input = dict(filter(lambda x: x[1], kwargs.items()))

        # Adjust input parameters to match specification for gNMI SubscribeRequest
        if 'mode' in input:
            input['mode'] = input['mode'].upper()
        input['encoding'] = self._encoding_value

        if 'prefix' in input:
            input['prefix'] = self._encodeXpath(input['prefix'])
        if 'subscription' in input:
            for item in input['subscription']:
                item['path'] = self._encodeXpath(item['path'])

        # Extract duration from input attributes
        if 'duration' in input:
            duration = input['duration']
            del input['duration']
        else:
            duration = 20

        request = json_format.ParseDict({'subscribe': input}, gnmi_pb2.SubscribeRequest())
        auth = self._login_credentials

        try:
            output = []
            responses = self._stub.Subscribe(iter([request]), duration, metadata=auth)

            if input['mode'] == 'ONCE':
                responses = [json_format.MessageToDict(response) for response in responses]
                output = self._mergeToSingleDict(responses)
            else:
                for update in self._simplifyUpdates(responses):
                    output.append(update)

        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                if input['mode'] == 'ONCE':
                    raise AnsibleConnectionFailure("gNMI ONCE Subscription timed out")
                else:
                    # RPC timed out, which is okay
                    pass
            else:
                raise AnsibleConnectionFailure("%s" % e)

        return json.dumps(output, indent=4).encode()
