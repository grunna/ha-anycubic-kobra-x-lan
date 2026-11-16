# Changelog

All notable changes to this project will be documented in this file.

## 0.2.0

### Added

- Bundled Lovelace card `custom:kobra-x-printer-card` (views `printer`, `details`, `camera`), served and loaded by the integration.
- Print event entity: started, paused, resumed, finished, stopped, failed, error (with reason code and text).
- Pause reason sensor with names for Anycubic's reason/error codes.
- Print preview and plate view image entities (job thumbnail via `file/fileDetails`).
- Firmware version on the device page.
- Every entity has a stable `translation_key`, so cards and automations can find it regardless of its name.

## 0.1.3

### Added

- Print control buttons: pause, resume, cancel.
- Print speed mode select, print speed and speed mode name sensors, estimated finish sensor, last print error sensor.
- Binary sensors: printing, print paused, print complete, print failed, print cancelled, axis moving, LAN connection, drying.
- Multi-color box (ACE): temperature and humidity sensors, drying start/stop buttons, drying temperature/duration settings, drying target/duration/remaining sensors, runout auto refill switch, retract filament button. Entities are created per box.
- Axis: home all, home X/Y, home Z, disable motors, read position buttons and X/Y/Z position sensors (disabled by default).
- Services `move_axis`, `start_drying` and `stop_drying`.
- Target temperature and fan controls also work while idle (`tempature/set`, `fan/setSpeed`).
- Camera entity is loaded again and plays the printer's HTTP-FLV stream.
- Camera stream switch is loaded.
- Camera card in the example dashboard.

### Fixed

- Polling no longer throws away state the printer pushed on its own (print progress, pause, drying, command replies); replies to commands are merged instead of replacing whole reports.
- Camera staying idle with no picture after a printer or Home Assistant restart: `startCapture` is now sent whenever the stream is opened and after the LAN connection reconnects.
- Kobra X `206 Partial Content` stream response is relayed as `200` so ffmpeg/go2rtc accept it.
- Filament slot sensors and lights reported after setup (e.g. when the multi-color box report misses the first refresh after a printer reboot) are now added automatically instead of only after a reload.
- MQTT connection now sends keepalive pings and reconnects when the printer stops answering (e.g. after a printer reboot).

## 0.1.2

### Fixed

- Tweaked for missing modelId for Kobra S1 Combo (Thanks fo grigorye)

## 0.1.1

### Added

- Print task sensors:
  - Print task
  - Print status
  - Print progress
  - Current layer
  - Total layers
  - Remaining print time
  - Print time
  - Filament used
  - Task ID

### Changed

- Removed the unstable camera entity from the loaded platforms.
- Camera stream URL is now exposed as an attribute on the Camera available binary sensor instead.

### Fixed

- Avoid Home Assistant camera proxy authentication errors caused by the unsupported FLV-style camera stream.

### Notes

- This version is still in progress.
- No release tag has been created yet.

## 0.1.0 - Initial HACS release

### Added

- Local setup by printer IP address.
- Printer state sensors.
- Nozzle and bed temperature sensors.
- Target nozzle and bed temperature controls.
- Fan speed sensors and controls.
- Firmware version sensor.
- Printer model and IP sensors.
- Feature information sensor.
- Multi-color box status sensor.
- Dynamic filament slot sensors.
- Camera entity.
- Camera light control.
- Refresh data button.
- Reconnect LAN connection button.
- Diagnostics support.
- HACS validation workflow.
- Hassfest validation workflow.
- Integration brand icon.

### Not included

- Firmware update checks.
- Print upload/start.
- Axis movement.
- Filament loading/unloading.
- Filament color changes.
- Cloud account features.
