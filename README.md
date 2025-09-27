# Web SCPI API

A RESTful-style web service that can enable access to SCPI-enabled equipment on
the network without having to install any of the propriatary software on your
local system.

# Endpoints

`/devices`

Lists the devices configured on the server.

`/devices/<device_name>`

Gets the information for a specific device, including identity information and
supported commands.

`/devices/<string:device_name>/<string:command>` (GET)

Queries the specified device using the referred command. Commands are defined
in the server configuration file. Arguments can be provided via arguments or
via JSON.

`/devices/<string:device_name>/<string:command>` (POST)

Configures the specified device using the referred command. Commands are
defined in the server configuration file. Arguments can be arguments or via
JSON.

# Configuration

The configuration for the server is a JSON file, and contains the port number,
remote device list, and other system configurations.

Each device that gets supported by the server gets a section under `devices`,
where the device name is the name of the section. Each device needs to have a
`host` field for the hostname or IP address for the test equipment. The
`identity` section lists out how to parse the device identity commands where
each element in the array maps to an element of the device's identity. The
`commands` section outlines the list of supported commands for both device
querries and updates, as well as their arguments and defaults.

For determining what the specific commands are for your device, consult the
programming guide from your device manufacturer for what SCPI commands are
supported by your equipment, their syntax, and their arguments. From there,
enter them into server configuration file, replacing arguments with
placeholders denoted by `{{ name }}`.

## Example Configuration

```json
{
    "port": 8080,
    "probe_on_start": true,
    "devices": {
        "psu": {
            "display_name": "Bench PSU",
            "host": "192.168.10.90",
            "port": 5025,
            "identity": [
                "Manufacturer",
                "Product Type",
                "Serial Number",
                "Software Version",
                "Hardware Version"
            ],
            "notes": "",
            "commands": {
                "voltage": {
                    "arguments": {
                        "channel": 1
                    },
                    "query": "MEASure:VOLTage? CH{{ channel }}"
                },
                "current": {
                    "arguments": {
                        "channel": 1
                    },
                    "query": "MEASure:CURRent? CH{{ channel }}"
                },
                "output": {
                    "arguments": {
                        "channel": 1,
                        "state": "OFF"
                    },
                    "update": "OUTPut CH{{ channel }},{{ state }}"
                }
            }
        },
        "o-scope": {
            "display_name": "Bench O-scope",
            "host": "192.168.10.91",
            "port": 5025,
            "identity": [
                "Manufacturer",
                "Product Type",
                "Serial Number",
                "Software Version"
            ],
            "notes": "",
            "commands": {
                "capture": {
                    "type": "bmp",
                    "payload_size": 768067,
                    "arguments": {
                    },
                    "query": "SCDP"
                }
            }
        },
        "multimeter":  {
            "display_name": "Bench Multimeter",
            "host": "192.168.10.93",
            "port": 5025,
            "identity": [
                "Manufacturer",
                "Product Type",
                "Serial Number",
                "Software Version",
                "Hardware Version"
            ],
            "notes": "",
            "commands": {
                "voltage": {
                    "arguments": {
                        "type": "DC",
                        "range": "AUTO"
                    },
                    "query": "MEASure:VOLTage:{{ type }}? {{ range }}"
                },
                "current": {
                    "arguments": {
                        "type": "DC",
                        "range": "AUTO"
                    },
                    "query": "MEASure:CURRent:{{ type }}? {{ range }}"
                }
            }
        }
    }
}
```
