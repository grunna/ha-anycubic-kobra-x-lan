# Anycubic Kobra X LAN

A Home Assistant custom integration for monitoring and controlling an Anycubic Kobra X printer over the local LAN.

This integration is focused on local printer access. It does not require an Anycubic cloud account for normal operation.

## Features

- Local setup by printer IP address
- Printer state sensor
- Nozzle and bed temperature sensors
- Target nozzle and bed temperature controls
- Fan speed sensors and controls
- Firmware version sensor
- Printer model and IP sensors
- Feature information sensor
- Multi-color box status
- Dynamic filament slot sensors
- Camera entity
- Camera light control
- Refresh data button
- Reconnect LAN connection button
- Diagnostics support

## Not included

The first release intentionally avoids features that are better handled from the slicer or require extra care:

- Firmware update checks
- Print upload/start
- Axis movement
- Filament loading/unloading
- Filament color changes
- Cloud account features

## Installation with HACS

This integration can be installed as a custom HACS repository.

1. Open Home Assistant.
2. Open HACS.
3. Open the three-dot menu.
4. Choose **Custom repositories**.
5. Add this repository URL.
6. Select category **Integration**.
7. Install **Anycubic Kobra X LAN**.
8. Restart Home Assistant.
9. Go to **Settings → Devices & services**.
10. Choose **Add integration**.
11. Search for **Anycubic Kobra X LAN**.
12. Enter your printer IP address.

## Setup

You need the printer IP address on your local network.

During setup, the integration connects to the printer, discovers the local LAN credentials, and shows the printer model before saving the integration.

Your Home Assistant instance and printer must be on the same local network.

## Supported printer

Currently tested with:

```text
Anycubic Kobra X
```

Other Anycubic printers may use a similar local protocol, but they are not confirmed yet.

## Camera

The integration exposes a camera entity when the printer reports that a camera is available.

The camera stream depends on the printer's local stream URL and Home Assistant's camera handling. Camera light control is exposed separately as a light entity.

## Controls

The integration includes basic controls for common Home Assistant use cases:

- Set target nozzle temperature
- Set target bed temperature
- Set model fan speed
- Set aux fan speed
- Set box/chamber fan speed
- Turn camera light on/off
- Refresh printer data
- Reconnect the LAN connection

Set nozzle or bed target temperature to `0` to turn heating off.

## Safety notes

Temperature and fan controls send commands directly to the printer over LAN.

This integration does not start prints, upload files, move printer motors, or perform filament loading/unloading operations.

Use the slicer for actions that require direct supervision, such as axis movement, filament changes, file upload, or starting a print.

## Local-only focus

This integration is designed around local LAN communication. Firmware checks and cloud features are intentionally not included in the first release.

## Troubleshooting

If the integration cannot connect, check that:

```text
The printer is turned on
The printer is connected to the same network as Home Assistant
LAN mode is enabled on the printer
The printer IP address is correct
No firewall is blocking local access
```

If the printer IP changes, you may need to remove and add the integration again, or set a fixed IP address for the printer in your router.

## Privacy

Printer data is read locally from your network.

This integration is not affiliated with Anycubic and does not send printer data to Anycubic cloud services for normal operation.

## Research and protocol notes

This Home Assistant integration is kept focused on the actual HACS implementation.

The reverse engineering notes, protocol research, test scripts, and technical explanations are kept in a separate research repository:

[anycubic-kobra-x-lan research repository](https://gitlab.com/grunna/anycubic-kobra-x-lan)

That repository contains more details about how the local LAN communication works, including MQTT topics, payloads, credential discovery, camera handling, and other protocol notes.

You do not need the research repository to use this integration. It is mainly intended for developers, contributors, and anyone who wants to understand or verify how the integration communicates with the printer.

## License

MIT License

## Disclaimer

This project is unofficial and not affiliated with Anycubic.

Use at your own risk. Printer firmware and local protocols may change over time.