from flask import Flask, jsonify, request
from time import sleep
from socket import socket, AF_INET, SOCK_STREAM
import logging
import json
import jinja2

app = Flask(__name__)
config = {}
_logger = logging.getLogger('web-scpi')


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

    if request.is_json:
        arguments.update(request.json)
    else:
        arguments.update(request.args)

    try:
        resp = send_scpi_command(
                device['host'],
                device['port'],
                generate_command_string(
                    device['commands'][command]['query'],
                    arguments,
                ),
                timeout=device.get('timeout')).decode().strip()
    except:
        return jsonify({
            'status': 'timeout',
        }), 500

    return jsonify({
        'status': 'ok',
        'data': resp,
    }), 200


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

    if request.is_json:
        arguments.update(request.json)
    else:
        arguments.update(request.args)

    try:
        resp = send_scpi_command(
                device['host'],
                device['port'],
                generate_command_string(
                    device['commands'][command]['update'],
                    arguments,
                ),
                recv_size=0,
                timeout=device.get('timeout')).decode().strip()
    except:
        return jsonify({
            'status': 'timeout',
        }), 500

    return jsonify({
        'status': 'ok',
    }), 200


def send_scpi_command(ip_addr, port, command, recv_size=1024, timeout=None, line_delay=0):
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.settimeout(timeout)

        sock.connect((ip_addr, int(port)))
        data = []

        for line in command.splitlines():
            _logger.info(f'Sending "{line}"')
            sock.sendall(str(line + '\n').encode())
            sleep(line_delay)
            data = sock.recv(recv_size)

    return data


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

    config_file = 'config.json'

    _logger.info(f'Loading configuration file from {config_file}')

    with open("config.json", mode="r") as f:
        config = json.load(f)

    devices = config.get('devices', {})

    _logger.info(f'Loaded {len(devices)} device configurations')

    for device in devices:
        _logger.debug(f'Contacting device at {devices[device]['host']}')
        try:
            devices[device]['identity'] = get_identity_info(devices[device])
        except:
            _logger.exception(f'Unable to get identity information for "{device}"')

    app.run(port=int(config.get('port', 8080)))
