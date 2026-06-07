# Anycubic Kobra X LAN

Local Home Assistant monitoring for Anycubic Kobra X printers.

This integration lets Home Assistant read information directly from your Anycubic Kobra X over your local network. You can see printer status, temperatures and other useful information in Home Assistant without relying on the Anycubic cloud for normal monitoring.

## Why use this integration?

Anycubic Kobra X LAN is built for users who want local printer visibility inside Home Assistant.

With this integration you can:

* See if your printer is idle, busy or offline
* Monitor nozzle and bed temperatures
* See target temperatures
* Check fan speed
* See firmware version
* Check if the camera is available
* Check USB and peripheral status
* Use printer data in Home Assistant dashboards and automations

The integration is designed to be read-only. It monitors your printer, but does not start prints, upload files, move motors or change printer settings.

## Supported printer

Currently tested with:

```text
Anycubic Kobra X
```

Other Anycubic printers may use a similar local protocol, but they are not confirmed yet.

## Requirements

You need:

```text
Home Assistant
HACS
Anycubic Kobra X connected to your local network
LAN mode enabled on the printer
The printer IP address
```

Your Home Assistant instance and printer must be on the same local network.

## Installation with HACS

This integration can be installed as a custom HACS repository.

1. Open Home Assistant
2. Open HACS
3. Open the three-dot menu
4. Choose **Custom repositories**
5. Add this repository URL
6. Select category **Integration**
7. Install **Anycubic Kobra X LAN**
8. Restart Home Assistant
9. Go to **Settings → Devices & services**
10. Choose **Add integration**
11. Search for **Anycubic Kobra X LAN**
12. Enter your printer IP address

After setup, Home Assistant will add the printer as a device and create the available sensors.

## Finding your printer IP address

You can usually find the printer IP address in your router, network settings or Anycubic/Orca-style slicer connection screen.

It will look something like:

```text
192.168.1.28
```

Use your own printer IP when adding the integration.

## Created sensors

The integration creates sensors such as:

```text
Printer state
Nozzle temperature
Bed temperature
Target nozzle temperature
Target bed temperature
Fan speed
Firmware version
Camera available
USB available
Multi color box available
```

The exact available sensors may depend on what the printer reports over LAN.

## Local communication

This integration is intended to communicate directly with the printer on your local network.

It does not need cloud access for normal local monitoring once the printer can be reached on LAN.

## Safety

This integration is read-only.

It does not:

```text
Start prints
Upload files
Move printer motors
Heat the nozzle
Heat the bed
Change printer settings
```

It only asks the printer for status information and displays that information in Home Assistant.

## Troubleshooting

If the integration cannot connect, check that:

```text
The printer is turned on
The printer is connected to the same network as Home Assistant
LAN mode is enabled on the printer
The printer IP address is correct
No firewall is blocking local access
```

If the printer IP changes, you may need to update the integration settings or set a fixed IP address for the printer in your router.

## Privacy

Printer data is read locally from your network.

This integration is not affiliated with Anycubic and does not send printer data to Anycubic cloud services.

## License

MIT License

## Disclaimer

This project is unofficial and not affiliated with Anycubic.

Use at your own risk. Printer firmware and local protocols may change over time.
