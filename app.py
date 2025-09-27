# Copyright (c) 2025 Ian Wakely
# SPDX-License-Identifier: Apache-2.0

from flask import Flask, jsonify, request, send_file
from time import sleep
from socket import socket, timeout, AF_INET, SOCK_STREAM
import logging
import json
import jinja2
from io import BytesIO

app = Flask(__name__)
config = {}
_logger = app.logger


@app.route('/devices')
def get_devices():
    _logger.debug('Requesting all device info')

    devices = config.get('devices', [])

    return jsonify({
        'status': 'ok',
        'devices': config.get('devices', []),
    }), 200


@app.route('/devices/<string:device_name>')
def get_device_info(device_name:str):
    _logger.debug(f'Requesting device info for device {device_name}')

    devices = config.get('devices', {})

    if device_name not in devices:
        return jsonify({
            'status': 'Invalid device name'
        }), 404

    devices[device_name]['identity'] = get_identity_info(devices[device_name])

    return jsonify({
        'status': 'ok',
        'device': devices[device_name],
    }), 200


@app.route('/devices/<string:device_name>/<string:command>', methods=['GET'])
def query_device(device_name:str, command:str):
    _logger.debug(f'Querying device configuration from device {device_name}')

    devices = config.get('devices', [])

    if device_name not in devices:
        return jsonify({
            'status': 'Invalid device name'
        }), 404

    device = devices[device_name]

    if command not in device.get('commands', {}):
        return jsonify({
            'status': 'Invalid device command'
        }), 404

    if 'query' not in device['commands'][command]:
        return jsonify({
            'status': 'Invalid device query'
        }), 400

    arguments = device['commands'][command].get('arguments', {})
    timeout = None
    payload_size = device['commands'][command].get('payload_size')

    if payload_size:
        timeout = device['commands'][command].get('timeout',
                    device.get('timeout',
                        config.get('timeout', 1)))

    if request.is_json:
        arguments.update(request.json)
    else:
        arguments.update(request.args)

    try:
        resp = send_scpi_command(
                device['host'],
                device.get('port', 5025),
                generate_command_string(
                    device['commands'][command]['query'],
                    arguments,
                ),
                recv_size=payload_size,
                timeout=timeout)
    except:
        _logger.exception('Failed to get data from device')
        return jsonify({
            'status': 'timeout',
        }), 500

    resp_type = device['commands'][command].get('type', 'string')

    if resp_type == 'string':
        return jsonify({
            'status': 'ok',
            'data': resp.decode().strip(),
        }), 200
    else:
        return send_file(
            BytesIO(resp),
            as_attachment=True,
            download_name=f'{command}.{resp_type}')


@app.route('/devices/<string:device_name>/<string:command>', methods=['POST'])
def update_device(device_name:str, command:str):
    _logger.debug(f'Updating configuration on device {device_name}')

    devices = config.get('devices', [])

    if device_name not in devices:
        return jsonify({
            'status': 'Invalid device name'
        }), 404

    device = devices[device_name]

    if command not in device.get('commands', {}):
        return jsonify({
            'status': 'Invalid device command'
        }), 404

    if 'update' not in device['commands'][command]:
        return jsonify({
            'status': 'Invalid device update'
        }), 400

    arguments = device['commands'][command].get('arguments', {})
    timeout = None
    payload_size = device['commands'][command].get('payload_size', 0)

    if payload_size:
        timeout = device['commands'][command].get('timeout',
                    device.get('timeout',
                        config.get('timeout', 1)))

    if request.is_json:
        arguments.update(request.json)
    else:
        arguments.update(request.args)

    try:
        resp = send_scpi_command(
                device['host'],
                device.get('port', 5025),
                generate_command_string(
                    device['commands'][command]['update'],
                    arguments,
                ),
                recv_size=payload_size,
                timeout=timeout)
    except:
        _logger.exception('Failed to get data from device')
        return jsonify({
            'status': 'timeout',
        }), 500

    return jsonify({
        'status': 'ok',
    }), 200


def send_scpi_command(ip_addr, port, command, recv_size=None, timeout=None, line_delay=0):
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.connect((ip_addr, int(port)))
        sock.settimeout(timeout)

        retval = []

        for line in command.splitlines():
            _logger.info(f'Sending "{line}"')
            sock.sendall(str(line + '\n').encode())

            sleep(line_delay)

            if recv_size is None:
                data = sock.recv(4096)
                retval += data
            else:
                try:
                    while len(retval) < recv_size:
                        data = sock.recv(recv_size - len(retval))
                        if not data:
                            break
                        retval += data
                except TimeoutError:
                    pass

    return bytes(retval)


def get_identity_info(device_config):
    resp = send_scpi_command(
            device_config['host'],
            device_config['port'],
            '*IDN?').decode().strip()

    if 'identity' in device_config:
        return dict(zip(device_config['identity'], resp.split(',')))

    return resp


def generate_command_string(input_string, values):
    template_environment = jinja2.Environment()
    template = template_environment.from_string(input_string)
    return template.render(values)


if __name__ == '__main__':
    from os import environ
    from pathlib import Path

    if "CONFIG_FILE" in environ:
        config_file = Path(environ.get("CONFIG_FILE"))
    else:
        config_file = Path(environ.get("CONFIG_DIR",
            environ.get("CODE_DIR", Path.home() / "config"))) /  'config.json'

    _logger.info(f'Loading configuration file from {config_file}')

    if not config_file.is_file():
        _logger.error("Unable to locate configuration file")
        exit(-1)

    with open(config_file, mode="r") as f:
        config = json.load(f)

    devices = config.get('devices', {})

    _logger.info(f'Loaded {len(devices)} device configurations')

    if config.get('probe_on_start', False):
        for device in devices:
            _logger.debug(f'Contacting device at {devices[device]['host']}')
            try:
                devices[device]['identity'] = get_identity_info(devices[device])
            except:
                _logger.exception(f'Unable to get identity information for "{device}"')

    app.run(
        host='0.0.0.0',
        port=int(config.get('port', environ.get("PORT_NUMBER")))
    )
