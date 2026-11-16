from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import socket
import ssl
import struct
import threading
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CAMERA_RESUME_WINDOW_SECONDS,
    CAMERA_CONFIRM_SECONDS,
    CAMERA_START_DEBOUNCE_SECONDS,
    CAMERA_STREAM_PORT,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    EVENT_ERROR,
    EVENT_FAILED,
    EVENT_FINISHED,
    EVENT_PAUSED,
    EVENT_RESUMED,
    EVENT_STARTED,
    EVENT_STOPPED,
    OPTIONAL_QUERY_TYPES,
    QUERY_TYPES,
)
from . import data as data_helpers

AXIS_Z = 3
AXIS_XY = 4
MOVE_TYPE_HOME = 2
FEED_TYPE_RETRACT = 2
DEFAULT_DRYING_TEMP = 45
DEFAULT_DRYING_DURATION = 240
# A decoded preview larger than this is a malfunction, not a picture.
MAX_PREVIEW_BYTES = 2 * 1024 * 1024

# Phase change -> event fired by the print event entity.
_PHASE_EVENTS = {
    (data_helpers.PHASE_PAUSED, data_helpers.PHASE_PRINTING): EVENT_RESUMED,
    (None, data_helpers.PHASE_PRINTING): EVENT_STARTED,
    (None, data_helpers.PHASE_PAUSED): EVENT_PAUSED,
    (None, data_helpers.PHASE_FINISHED): EVENT_FINISHED,
    (None, data_helpers.PHASE_STOPPED): EVENT_STOPPED,
    (None, data_helpers.PHASE_FAILED): EVENT_FAILED,
}

_LOGGER = logging.getLogger(__name__)


class AnycubicKobraXLanCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        polling_interval = entry.options.get(
            CONF_POLLING_INTERVAL,
            DEFAULT_POLLING_INTERVAL,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
        )
        self.entry = entry
        self.credentials: dict[str, Any] = entry.data["credentials"]
        self._mqtt = _PersistentRawMqttClient(
            self.credentials,
            self._handle_report_from_thread,
            self._handle_connected_from_thread,
        )
        self.drying_target_temp = DEFAULT_DRYING_TEMP
        self.drying_duration = DEFAULT_DRYING_DURATION
        self._camera_start_lock = asyncio.Lock()
        self._camera_last_start = 0.0
        self._camera_last_requested = 0.0
        # Renders of the running job, answered to a file/fileDetails request.
        self.print_previews: dict[str, bytes] = {}
        self.print_preview_filename: str | None = None
        self.print_preview_updated: datetime | None = None
        self._file_details_requested: str | None = None
        # Print events.
        self._job_phase: str | None = None
        self._error_code: int | None = None
        self._event_listeners: list[Callable[[str, dict[str, Any]], None]] = []
        self._sw_version: str | None = None
        self.async_add_listener(self._async_after_update)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            reports = await self.hass.async_add_executor_job(
                self._mqtt.query_all_and_wait
            )
        except Exception as err:
            raise UpdateFailed(str(err)) from err

        # Keep everything the printer pushed on its own (print progress,
        # drying, command replies, camera state) and lay fresh answers on top.
        data = dict(self.data or {})

        for report_type, payload in reports.items():
            self._apply_report(data, report_type, payload)

        return data

    @callback
    def async_push_data(self, data: dict[str, Any]) -> None:
        """Publish data the printer pushed on its own (or an optimistic state).

        Unlike async_set_updated_data this does not reschedule the poll. The
        printer pushes progress, video and command replies every few seconds
        while printing or streaming; rescheduling on each of them pushed the
        poll back forever, so temperatures, layers etc. froze.
        """
        self.data = data
        self.last_update_success = True
        self.async_update_listeners()

    async def async_shutdown(self) -> None:
        await self.hass.async_add_executor_job(self._mqtt.stop)

    async def async_reconnect(self) -> None:
        await self.hass.async_add_executor_job(self._mqtt.reconnect)
        await self.async_request_refresh()

    async def async_set_light(
        self,
        light_type: int,
        status: int,
        brightness: int,
    ) -> None:
        await self.hass.async_add_executor_job(
            self._mqtt.set_light,
            light_type,
            status,
            brightness,
        )

        new_data = dict(self.data or {})
        light_report = dict(new_data.get("light") or {})
        light_data = light_report.get("data")

        if isinstance(light_data, dict):
            light_data = dict(light_data)
        else:
            light_data = {}

        lights = light_data.get("lights")

        if isinstance(lights, list):
            lights = [
                dict(item) if isinstance(item, dict) else item
                for item in lights
            ]
        else:
            lights = []

        found = False

        for item in lights:
            if isinstance(item, dict) and item.get("type") == light_type:
                item["status"] = status
                item["brightness"] = brightness
                found = True
                break

        if not found:
            lights.append(
                {
                    "type": light_type,
                    "status": status,
                    "brightness": brightness,
                }
            )

        light_data["lights"] = lights
        light_report["data"] = light_data
        light_report["type"] = "light"
        light_report["action"] = "control"
        new_data["light"] = light_report

        self.async_push_data(new_data)

    async def async_set_camera_stream(self, enabled: bool) -> None:
        if enabled:
            await self.async_start_camera(force=True)
            return

        self._camera_last_requested = 0.0
        await self.hass.async_add_executor_job(
            self._mqtt.set_camera_stream,
            "stopCapture",
        )
        self._set_camera_stream_optimistic(False, "stopCapture")

    async def async_start_camera(self, force: bool = False) -> None:
        """Ask the printer to push video to its local HTTP-FLV endpoint.

        The printer keeps the stream endpoint closed after a reboot (and after
        it drops the MQTT session) until startCapture is published again, so
        this is called every time Home Assistant opens the stream.
        """
        self._camera_last_requested = time.monotonic()

        async with self._camera_start_lock:
            now = time.monotonic()

            if (
                not force
                and now - self._camera_last_start < CAMERA_START_DEBOUNCE_SECONDS
            ):
                return

            camera_stream = (self.data or {}).get("camera_stream") or {}
            enabled = bool(camera_stream.get("enabled"))
            confirmed = enabled and not camera_stream.get("optimistic")
            waiting = (
                enabled
                and camera_stream.get("optimistic")
                and now - self._camera_last_start < CAMERA_CONFIRM_SECONDS
            )

            if not force and (confirmed or waiting):
                # Already pushing (or just asked to): sending stop/start again
                # would cut the stream every viewer is watching.
                return

            self._camera_last_start = now

            try:
                if force or not enabled:
                    # AnycubicSlicerNext sends stopCapture first and waits
                    # briefly; some firmwares ignore a bare startCapture when
                    # the previous capture session was not closed cleanly.
                    await self.hass.async_add_executor_job(
                        self._mqtt.set_camera_stream,
                        "stopCapture",
                    )
                    await asyncio.sleep(1)

                await self.hass.async_add_executor_job(
                    self._mqtt.set_camera_stream,
                    "startCapture",
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Could not start the camera stream: %s", err)
                return

            self._set_camera_stream_optimistic(True, "startCapture")

    @callback
    def async_camera_stalled(self) -> None:
        self._camera_last_start = 0.0
        self._set_camera_stream_optimistic(False, "stalled")

    def camera_stream_url(self) -> str | None:
        """Return the printer's local HTTP-FLV stream URL."""
        info = (self.data or {}).get("info")

        if isinstance(info, dict):
            payload = info.get("data") if isinstance(info.get("data"), dict) else info
            urls = payload.get("urls")

            if isinstance(urls, dict):
                stream_url = urls.get("rtspUrl")

                if isinstance(stream_url, str) and stream_url:
                    return stream_url

        host = self.credentials.get("ip")

        if host:
            return f"http://{host}:{CAMERA_STREAM_PORT}/flv"

        return None

    def _set_camera_stream_optimistic(self, enabled: bool, action: str) -> None:
        new_data = dict(self.data or {})
        camera_stream = dict(new_data.get("camera_stream") or {})
        camera_stream["enabled"] = enabled
        camera_stream["last_action"] = action
        camera_stream["optimistic"] = True
        new_data["camera_stream"] = camera_stream
        self.async_push_data(new_data)

    def _handle_connected_from_thread(self) -> None:
        self.hass.loop.call_soon_threadsafe(self._handle_connected_on_loop)

    def _handle_connected_on_loop(self) -> None:
        # A new MQTT session means the printer (or the connection) restarted,
        # so any capture session it had is gone.
        if self.data and isinstance(self.data.get("camera_stream"), dict):
            new_data = dict(self.data)
            camera_stream = dict(new_data["camera_stream"])
            camera_stream["enabled"] = False
            camera_stream["optimistic"] = True
            new_data["camera_stream"] = camera_stream
            self.async_push_data(new_data)

        # Resume a stream somebody was watching when the connection dropped.
        # A start already in flight opened this connection itself.
        if (
            not self._camera_start_lock.locked()
            and self._camera_last_requested
            and time.monotonic() - self._camera_last_requested
            < CAMERA_RESUME_WINDOW_SECONDS
        ):
            self._camera_last_start = 0.0
            self.hass.async_create_task(self.async_start_camera())

    async def async_send_command(
        self,
        message_type: str,
        action: str,
        data: dict[str, Any] | None = None,
        refresh: bool = True,
    ) -> None:
        await self.hass.async_add_executor_job(
            self._mqtt.publish_command,
            message_type,
            action,
            data,
        )

        if refresh:
            await self.async_request_refresh()

    async def async_print_control(self, action: str) -> None:
        """Pause, resume or stop the running job (print/<action>)."""
        current_task_id = data_helpers.task_id(self.data or {})

        if not current_task_id:
            raise HomeAssistantError("No print job is running")

        await self.async_send_command("print", action, {"taskid": current_task_id})

    async def async_set_print_speed_mode(self, mode: int) -> None:
        await self.async_set_print_setting("print_speed_mode", int(mode))

    async def async_set_drying(
        self,
        box_index: int,
        enabled: bool,
        target_temp: int | None = None,
        duration: int | None = None,
    ) -> None:
        data = self.data or {}
        await self.async_send_command(
            "multiColorBox",
            "setDry",
            {
                "multi_color_box": [
                    {
                        "id": data_helpers.box_id(data, box_index),
                        "drying_status": {
                            "status": 1 if enabled else 0,
                            "target_temp": int(
                                target_temp
                                if target_temp is not None
                                else self.drying_target_temp
                            ),
                            "duration": int(
                                duration if duration is not None else self.drying_duration
                            )
                            if enabled
                            else 0,
                            "remain_time": None,
                        },
                    }
                ]
            },
        )

    async def async_set_auto_feed(self, box_index: int, enabled: bool) -> None:
        data = self.data or {}
        await self.async_send_command(
            "multiColorBox",
            "setAutoFeed",
            {
                "multi_color_box": [
                    {
                        "id": data_helpers.box_id(data, box_index),
                        "auto_feed": int(enabled),
                    }
                ]
            },
        )

    async def async_retract_filament(self, box_index: int) -> None:
        data = self.data or {}
        await self.async_send_command(
            "multiColorBox",
            "feedFilament",
            {
                "multi_color_box": [
                    {
                        "id": data_helpers.box_id(data, box_index),
                        "feed_status": {"slot_index": -1, "type": FEED_TYPE_RETRACT},
                    }
                ]
            },
        )

    async def async_move_axis(
        self,
        axis: int,
        move_type: int,
        distance: int = 0,
    ) -> None:
        """axis 1 X, 2 Y, 3 Z, 4 X+Y; move_type 0 minus, 1 plus, 2 home."""
        if data_helpers.print_in_progress(self.data or {}):
            raise HomeAssistantError("Axes cannot be moved while printing")

        await self.async_send_command(
            "axis",
            "move",
            {"axis": int(axis), "move_type": int(move_type), "distance": int(distance)},
            refresh=False,
        )

    async def async_home_all_axes(self) -> None:
        # Axis 4 homes X and Y only; Z needs its own home once XY is done.
        await self.async_move_axis(AXIS_XY, MOVE_TYPE_HOME)
        await self._async_wait_for_axis_move()
        await self.async_move_axis(AXIS_Z, MOVE_TYPE_HOME)
        await self._async_wait_for_axis_move()
        await self.async_query_axis_position()

    async def _async_wait_for_axis_move(self, timeout: float = 120) -> None:
        await asyncio.sleep(2)
        end = time.monotonic() + timeout

        while time.monotonic() < end:
            state = data_helpers.axis_move_state(self.data or {})

            if state in (None, "done", "failed"):
                return

            await asyncio.sleep(1)

    async def async_motors_off(self) -> None:
        await self.async_send_command("axis", "turnOff", None, refresh=False)

    async def async_query_axis_position(self) -> None:
        await self.async_send_command("axis", "query", {}, refresh=False)

    @property
    def mqtt_connected(self) -> bool:
        return self._mqtt.is_connected

    async def async_set_target_temperature(
        self,
        setting_key: str,
        temperature: int,
    ) -> None:
        await self.async_set_print_setting(setting_key, int(temperature))

    async def async_set_print_setting(
        self,
        setting_key: str,
        value: int,
    ) -> None:
        current = self.data or {}
        task_id = data_helpers.task_id(current)
        settings = {
            setting_key: int(value),
        }

        if data_helpers.print_in_progress(current) and task_id:
            await self.hass.async_add_executor_job(
                self._mqtt.set_print_settings,
                task_id,
                settings,
            )
        elif setting_key in ("target_hotbed_temp", "target_nozzle_temp"):
            # Without a job print/update is ignored; tempature/set is what
            # the slicer's preheat uses (type 0 nozzle, 1 bed).
            await self.hass.async_add_executor_job(
                self._mqtt.publish_command,
                "tempature",
                "set",
                {
                    "type": 0 if setting_key == "target_nozzle_temp" else 1,
                    "target_nozzle_temp": int(value)
                    if setting_key == "target_nozzle_temp"
                    else 0,
                    "target_hotbed_temp": int(value)
                    if setting_key == "target_hotbed_temp"
                    else 0,
                },
            )
        elif setting_key in ("fan_speed_pct", "aux_fan_speed_pct", "box_fan_level"):
            await self.hass.async_add_executor_job(
                self._mqtt.publish_command,
                "fan",
                "setSpeed",
                settings,
            )
        else:
            raise HomeAssistantError("This setting can only be changed while printing")

        new_data = dict(self.data or {})

        if setting_key in ("target_hotbed_temp", "target_nozzle_temp"):
            tempature = dict(new_data.get("tempature") or {})
            temp_data = tempature.get("data")

            if isinstance(temp_data, dict):
                temp_data = dict(temp_data)
                temp_data[setting_key] = int(value)
                tempature["data"] = temp_data
            else:
                tempature[setting_key] = int(value)

            new_data["tempature"] = tempature
        elif setting_key in ("fan_speed_pct", "aux_fan_speed_pct", "box_fan_level"):
            fan = dict(new_data.get("fan") or {})
            fan_data = fan.get("data")

            if isinstance(fan_data, dict):
                fan_data = dict(fan_data)
                fan_data[setting_key] = int(value)
                fan["data"] = fan_data
            else:
                fan[setting_key] = int(value)

            new_data["fan"] = fan

        self.async_push_data(new_data)

    def _handle_report_from_thread(self, report_type: str, payload: dict[str, Any]) -> None:
        self.hass.loop.call_soon_threadsafe(
            self._handle_report_on_loop,
            report_type,
            payload,
        )

    def _handle_report_on_loop(self, report_type: str, payload: dict[str, Any]) -> None:
        new_data = dict(self.data or {})
        self._apply_report(new_data, report_type, payload)
        self.async_push_data(new_data)

    # ----- print preview -------------------------------------------------

    def _apply_file_details(self, payload: dict[str, Any]) -> None:
        report = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        details = report.get("file_details")

        if not isinstance(details, dict):
            return

        filename = report.get("filename")
        current = data_helpers.project(self.data or {}).get("filename")

        if filename and current and filename != current:
            # A late answer for the previous job.
            return

        previews: dict[str, bytes] = {}

        for name, key in (("thumbnail", "thumbnail"), ("plate", "png_image")):
            raw = _decode_image(details.get(key))

            if raw is not None:
                previews[name] = raw

        if not previews:
            return

        self.print_previews = previews
        self.print_preview_filename = filename or current
        self.print_preview_updated = dt_util.utcnow()

    @callback
    def _async_request_file_details(self) -> None:
        """Ask once per job for its thumbnail; the printer never pushes it."""
        data = self.data or {}

        if not data_helpers.print_in_progress(data):
            return

        filename = data_helpers.project(data).get("filename")

        if not filename or filename == self._file_details_requested:
            return

        self._file_details_requested = filename
        self.hass.async_create_task(self._async_send_file_details(str(filename)))

    async def _async_send_file_details(self, filename: str) -> None:
        try:
            await self.async_send_command(
                "file",
                "fileDetails",
                {"root": "local", "filename": filename, "plate_index": 1},
                refresh=False,
            )
        except Exception as err:  # noqa: BLE001 - optional feature
            _LOGGER.debug("fileDetails request failed: %s", err)

    # ----- print events --------------------------------------------------

    @callback
    def async_add_event_listener(
        self, listener: Callable[[str, dict[str, Any]], None]
    ) -> CALLBACK_TYPE:
        self._event_listeners.append(listener)

        @callback
        def _remove() -> None:
            if listener in self._event_listeners:
                self._event_listeners.remove(listener)

        return _remove

    @callback
    def _fire_event(self, event_type: str, attributes: dict[str, Any]) -> None:
        for listener in list(self._event_listeners):
            listener(event_type, attributes)

    @callback
    def _async_after_update(self) -> None:
        data = self.data or {}
        self._async_request_file_details()
        self._async_update_sw_version(data)

        phase = data_helpers.job_phase(data)
        previous = self._job_phase
        self._job_phase = phase
        reason = data_helpers.print_reason(data)
        project = data_helpers.project(data)
        attributes: dict[str, Any] = {
            "task": project.get("filename") or project.get("name"),
            "progress": project.get("progress"),
        }

        if reason:
            attributes["reason_code"] = reason["code"]
            attributes["reason"] = reason["reason"]

            if not reason["by_user"] and reason["code"] != self._error_code:
                self._error_code = reason["code"]
                self._fire_event(EVENT_ERROR, attributes)
        elif phase == data_helpers.PHASE_PRINTING:
            self._error_code = None

        if previous is None or previous == phase:
            # Nothing seen before a restart counts as an event.
            return

        if phase == data_helpers.PHASE_IDLE:
            return

        event = _PHASE_EVENTS.get((previous, phase)) or _PHASE_EVENTS.get((None, phase))

        if event == EVENT_STARTED and previous == data_helpers.PHASE_PAUSED:
            event = EVENT_RESUMED

        if event:
            self._fire_event(event, attributes)

    @callback
    def _async_update_sw_version(self, data: dict[str, Any]) -> None:
        version = data_helpers.payload(data, "info").get("version")

        if not version or version == self._sw_version:
            return

        self._sw_version = str(version)
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(
            identifiers={(DOMAIN, self.credentials["deviceId"])}
        )

        if device is not None and device.sw_version != self._sw_version:
            registry.async_update_device(device.id, sw_version=self._sw_version)

    def _apply_report(
        self,
        data: dict[str, Any],
        report_type: str,
        payload: dict[str, Any],
    ) -> None:
        if report_type == "light":
            self._update_light_state(data, payload)
        elif report_type == "video":
            data["video"] = payload
            self._update_camera_stream_state(data, payload)
        elif report_type == "multiColorBox":
            _merge_multi_color_box(data, payload)
        elif report_type == "axis" and payload.get("action") == "move":
            # Move replies carry no coordinates; keep the last known position.
            data["axis_move"] = payload
        elif report_type == "file":
            # Large base64 renders: kept as bytes on the coordinator, never in data.
            self._apply_file_details(payload)
        elif report_type in ("tempature", "fan"):
            # Replies to set commands may carry only the changed value.
            data[report_type] = _merge_report(data.get(report_type), payload)
        else:
            data[report_type] = payload

    def _update_light_state(
        self,
        data: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        payload_data = payload.get("data")

        if not isinstance(payload_data, dict):
            data["light"] = payload
            return

        if isinstance(payload_data.get("lights"), list):
            data["light"] = payload
            return

        light_type = payload_data.get("type")

        if light_type is None:
            data["light"] = payload
            return

        light_report = dict(data.get("light") or {})
        light_report["type"] = "light"
        light_report["action"] = payload.get("action", "control")

        light_data = light_report.get("data")

        if isinstance(light_data, dict):
            light_data = dict(light_data)
        else:
            light_data = {}

        lights = light_data.get("lights")

        if isinstance(lights, list):
            lights = [
                dict(item) if isinstance(item, dict) else item
                for item in lights
            ]
        else:
            lights = []

        found = False

        for item in lights:
            if not isinstance(item, dict):
                continue

            if str(item.get("type")) == str(light_type):
                item["type"] = light_type
                item["status"] = payload_data.get("status")
                item["brightness"] = payload_data.get("brightness")
                found = True
                break

        if not found:
            lights.append(
                {
                    "type": light_type,
                    "status": payload_data.get("status"),
                    "brightness": payload_data.get("brightness"),
                }
            )

        light_data["lights"] = lights
        light_report["data"] = light_data
        data["light"] = light_report

    def _update_camera_stream_state(
        self,
        data: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        state = payload.get("state")
        action = payload.get("action")
        code = payload.get("code")

        camera_stream = dict(data.get("camera_stream") or {})
        camera_stream["last_action"] = action
        camera_stream["last_state"] = state
        camera_stream["last_code"] = code
        camera_stream["optimistic"] = False

        if state == "initSuccess":
            camera_stream["enabled"] = True
        elif state in ("pushStopped", "pushFailed", "initFailed"):
            camera_stream["enabled"] = False

        response_data = payload.get("data")

        if isinstance(response_data, dict):
            urls = response_data.get("urls")

            if isinstance(urls, dict):
                stream_url = urls.get("rtspUrl")

                if isinstance(stream_url, str) and stream_url:
                    camera_stream["stream_url_available"] = True

        data["camera_stream"] = camera_stream


class _PersistentRawMqttClient:
    def __init__(
        self,
        credentials: dict[str, Any],
        on_report,
        on_connect=None,
    ) -> None:
        self.credentials = credentials
        self.on_report = on_report
        self.on_connect = on_connect

        parsed = urlparse(credentials["broker"])
        self.host = parsed.hostname or credentials["ip"]
        self.port = parsed.port or 9883

        self.username = credentials["username"]
        self.password = credentials["password"]
        self.device_id = credentials["deviceId"]
        self.mode_id = str(credentials.get("modeId") or credentials.get("modelId"))

        self.subscribe_topic = f"anycubic/anycubicCloud/v1/printer/+/{self.mode_id}/{self.device_id}/#"
        self.client_id = f"ha_anycubic_{self.device_id[-8:]}"

        self._lock = threading.RLock()
        self._latest_lock = threading.RLock()
        self._latest: dict[str, Any] = {}
        self._latest_time: dict[str, float] = {}

        self._sock = None
        self._last_rx = 0.0
        self._last_ping = 0.0
        self._stop_event = threading.Event()
        self._reader_thread: threading.Thread | None = None

    def start(self) -> None:
        with self._lock:
            if self._reader_thread and self._reader_thread.is_alive():
                return

            self._stop_event.clear()
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                name="anycubic-kobra-x-lan-mqtt",
                daemon=True,
            )
            self._reader_thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        with self._lock:
            self._close_locked()

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=5)

    def reconnect(self) -> None:
        with self._lock:
            self._close_locked()
            self._ensure_connected_locked()

    @property
    def is_connected(self) -> bool:
        return self._sock is not None

    def query_all_and_wait(self) -> dict[str, Any]:
        """Ask for every report and return the answers received for it."""
        self.start()
        self._ensure_connected()

        started = time.monotonic()
        expected = set(QUERY_TYPES)

        for query_type in QUERY_TYPES:
            self._publish_query(query_type)

        # Printers without these stay silent, so they are not waited for.
        for query_type in OPTIONAL_QUERY_TYPES:
            self._publish_query(query_type)

        end_time = started + 8

        while time.monotonic() < end_time:
            with self._latest_lock:
                fresh = {
                    key
                    for key, received in self._latest_time.items()
                    if received >= started
                }

            if expected.issubset(fresh):
                break

            time.sleep(0.1)

        with self._latest_lock:
            return {
                key: value
                for key, value in self._latest.items()
                if self._latest_time.get(key, 0) >= started
            }

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._ensure_connected()

                with self._lock:
                    sock = self._sock

                if sock is None:
                    time.sleep(1)
                    continue

                self._keepalive(sock)

                try:
                    packet_type, body = _read_packet(sock)
                except (TimeoutError, socket.timeout):
                    continue

                if packet_type is None:
                    self._mark_disconnected()
                    continue

                self._last_rx = time.monotonic()

                if (packet_type & 0xF0) != 0x30:
                    continue

                topic, payload = _decode_publish(body)

                if not isinstance(payload, dict):
                    continue

                report_type = _report_type_from_topic_and_payload(topic, payload)

                if report_type == "unknown":
                    continue

                with self._latest_lock:
                    self._latest[report_type] = payload
                    self._latest_time[report_type] = time.monotonic()

                self.on_report(report_type, payload)
            except Exception as err:
                _LOGGER.debug("MQTT reader error, reconnecting: %s", err)
                self._mark_disconnected()
                time.sleep(2)

    def _keepalive(self, sock) -> None:
        # Without PINGREQ a printer that rebooted leaves a half-open socket
        # behind and the reader never notices, so nothing (including the
        # camera) recovers until Home Assistant is restarted.
        now = time.monotonic()

        if now - self._last_rx > MQTT_KEEPALIVE_SECONDS * 1.5:
            _LOGGER.debug("No MQTT traffic from printer, reconnecting")
            self._mark_disconnected()
            return

        if now - self._last_ping >= MQTT_KEEPALIVE_SECONDS / 2:
            self._last_ping = now

            with self._lock:
                if self._sock is sock:
                    sock.sendall(_PINGREQ_PACKET)

    def set_light(
        self,
        light_type: int,
        status: int,
        brightness: int,
    ) -> None:
        publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/light"
        payload = _build_light_control_payload(light_type, status, brightness)

        with self._lock:
            self._ensure_connected_locked()

            if self._sock is None:
                raise RuntimeError("MQTT socket is not connected")

            self._sock.sendall(_publish_packet(publish_topic, payload))

    def set_camera_stream(self, action: str) -> None:
        publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/video"
        payload = _build_video_capture_payload(action)

        with self._lock:
            self._ensure_connected_locked()

            if self._sock is None:
                raise RuntimeError("MQTT socket is not connected")

            self._sock.sendall(_publish_packet(publish_topic, payload))

    def publish_command(
        self,
        message_type: str,
        action: str,
        data: dict[str, Any] | None,
    ) -> None:
        publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/{message_type}"
        payload = {
            "type": message_type,
            "action": action,
            "timestamp": int(time.time() * 1000),
            "msgid": str(uuid.uuid4()),
            "data": data,
        }

        with self._lock:
            self._ensure_connected_locked()

            if self._sock is None:
                raise RuntimeError("MQTT socket is not connected")

            self._sock.sendall(_publish_packet(publish_topic, payload))

    def set_print_settings(
        self,
        task_id: str,
        settings: dict[str, Any],
    ) -> None:
        publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/print"
        payload = _build_print_update_payload(task_id, settings)

        with self._lock:
            self._ensure_connected_locked()

            if self._sock is None:
                raise RuntimeError("MQTT socket is not connected")

            self._sock.sendall(_publish_packet(publish_topic, payload))

    def _publish_query(self, query_type: str) -> None:
        publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/{query_type}"
        payload = _build_query_payload(query_type)

        with self._lock:
            self._ensure_connected_locked()

            if self._sock is None:
                raise RuntimeError("MQTT socket is not connected")

            self._sock.sendall(_publish_packet(publish_topic, payload))

    def _ensure_connected(self) -> None:
        with self._lock:
            self._ensure_connected_locked()

    def _ensure_connected_locked(self) -> None:
        if self._sock is not None:
            return

        context = ssl._create_unverified_context()

        raw = socket.create_connection((self.host, self.port), timeout=10)
        sock = context.wrap_socket(raw, server_hostname=self.host)
        sock.settimeout(10)

        try:
            sock.sendall(_connect_packet(self.client_id, self.username, self.password))
            packet_type, body = _read_packet(sock)

            if packet_type != 0x20 or len(body) < 2 or body[1] != 0:
                raise RuntimeError(f"MQTT connection rejected: {body.hex()}")

            sock.sendall(_subscribe_packet(self.subscribe_topic))
            packet_type, body = _read_packet(sock)

            if packet_type != 0x90:
                raise RuntimeError(f"MQTT subscribe failed: packet={packet_type!r}, body={body.hex()}")

            sock.settimeout(1)
            self._sock = sock
            self._last_rx = self._last_ping = time.monotonic()
            _LOGGER.debug("Connected to Anycubic LAN MQTT broker")
        except Exception:
            try:
                sock.close()
            finally:
                raise

        if self.on_connect is not None:
            try:
                self.on_connect()
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("MQTT on_connect callback failed: %s", err)

    def _mark_disconnected(self) -> None:
        with self._lock:
            self._close_locked()

    def _close_locked(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            finally:
                self._sock = None


MQTT_KEEPALIVE_SECONDS = 60
_PINGREQ_PACKET = bytes([0xC0, 0x00])


def _enc_str(value: bytes) -> bytes:
    return struct.pack("!H", len(value)) + value


def _enc_remaining_length(length: int) -> bytes:
    out = bytearray()

    while True:
        digit = length % 128
        length //= 128

        if length:
            digit |= 0x80

        out.append(digit)

        if not length:
            return bytes(out)


def _packet(packet_type: int, body: bytes) -> bytes:
    return bytes([packet_type]) + _enc_remaining_length(len(body)) + body


def _read_exact(sock, length: int) -> bytes:
    body = b""

    while len(body) < length:
        chunk = sock.recv(length - len(body))

        if not chunk:
            raise ConnectionError("Socket closed while reading packet")

        body += chunk

    return body


def _read_remaining_length(sock) -> int:
    multiplier = 1
    value = 0

    while True:
        b = _read_exact(sock, 1)[0]
        value += (b & 127) * multiplier

        if (b & 128) == 0:
            return value

        multiplier *= 128

        if multiplier > 128 * 128 * 128:
            raise ValueError("Malformed MQTT remaining length")


def _read_packet(sock):
    first = sock.recv(1)

    if not first:
        return None, None

    packet_type = first[0]
    remaining = _read_remaining_length(sock)
    body = _read_exact(sock, remaining)

    return packet_type, body


def _connect_packet(client_id: str, username: str, password: str) -> bytes:
    body = (
        _enc_str(b"MQTT")
        + bytes([4, 0xC2])
        + struct.pack("!H", MQTT_KEEPALIVE_SECONDS)
        + _enc_str(client_id.encode("utf-8"))
        + _enc_str(username.encode("utf-8"))
        + _enc_str(password.encode("utf-8"))
    )

    return _packet(0x10, body)


def _subscribe_packet(topic: str, packet_id: int = 1) -> bytes:
    body = (
        struct.pack("!H", packet_id)
        + _enc_str(topic.encode("utf-8"))
        + bytes([0])
    )

    return _packet(0x82, body)


def _publish_packet(topic: str, payload: dict[str, Any]) -> bytes:
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    body = _enc_str(topic.encode("utf-8")) + payload_bytes

    return _packet(0x30, body)


def _build_query_payload(query_type: str) -> dict[str, Any]:
    return {
        "type": query_type,
        "action": "getInfo" if query_type == "multiColorBox" else "query",
        "timestamp": int(time.time() * 1000),
        "msgid": str(uuid.uuid4()),
        "data": None,
    }


def _build_light_control_payload(
    light_type: int,
    status: int,
    brightness: int,
) -> dict[str, Any]:
    return {
        "type": "light",
        "action": "control",
        "timestamp": int(time.time() * 1000),
        "msgid": str(uuid.uuid4()),
        "data": {
            "type": light_type,
            "status": status,
            "brightness": brightness,
        },
    }


def _build_video_capture_payload(action: str) -> dict[str, Any]:
    return {
        "type": "video",
        "action": action,
        "timestamp": int(time.time() * 1000),
        "msgid": str(uuid.uuid4()),
        "data": None,
    }


def _build_print_update_payload(
    task_id: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "print",
        "action": "update",
        "timestamp": int(time.time() * 1000),
        "msgid": str(uuid.uuid4()),
        "data": {
            "taskid": str(task_id or ""),
            "settings": settings,
        },
    }


def _merge_report(previous: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(previous, dict):
        return payload

    merged = {**previous, **payload}
    previous_data = previous.get("data")
    new_data = payload.get("data")

    if isinstance(previous_data, dict) and isinstance(new_data, dict):
        merged["data"] = {**previous_data, **new_data}
    elif new_data is None and isinstance(previous_data, dict):
        merged["data"] = previous_data

    return merged


def _merge_multi_color_box(data: dict[str, Any], payload: dict[str, Any]) -> None:
    """Merge box updates by id so a reply to setDry/setAutoFeed (which only
    carries the changed fields) does not wipe the slot list."""
    previous = data.get("multiColorBox")
    new_data = payload.get("data")

    if not isinstance(previous, dict) or not isinstance(new_data, dict):
        if isinstance(new_data, dict):
            data["multiColorBox"] = payload
        return

    merged = _merge_report(previous, payload)
    old_boxes = (previous.get("data") or {}).get("multi_color_box")
    new_boxes = new_data.get("multi_color_box")

    if isinstance(old_boxes, list) and isinstance(new_boxes, list):
        boxes = [dict(box) if isinstance(box, dict) else box for box in old_boxes]

        for index, new_box in enumerate(new_boxes):
            if not isinstance(new_box, dict):
                continue

            target = None

            for old_index, box in enumerate(boxes):
                if isinstance(box, dict) and box.get("id", old_index) == new_box.get(
                    "id", index
                ):
                    target = box
                    break

            if target is None:
                boxes.append(dict(new_box))
                continue

            for key, value in new_box.items():
                if isinstance(value, dict) and isinstance(target.get(key), dict):
                    target[key] = {**target[key], **value}
                else:
                    target[key] = value

        merged["data"] = {**merged["data"], "multi_color_box": boxes}

    data["multiColorBox"] = merged


def _report_type_from_topic_and_payload(
    topic: str,
    payload: dict[str, Any],
) -> str:
    payload_type = payload.get("type")

    if isinstance(payload_type, str) and payload_type:
        return payload_type

    parts = topic.split("/")

    if len(parts) >= 2 and parts[-1] == "report":
        return parts[-2]

    if parts:
        return parts[-1]

    return "unknown"


def _decode_image(value: Any) -> bytes | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None

    if len(raw) > MAX_PREVIEW_BYTES:
        return None

    return raw


def _decode_publish(body: bytes):
    topic_len = struct.unpack("!H", body[:2])[0]
    topic = body[2 : 2 + topic_len].decode("utf-8", errors="replace")
    payload = body[2 + topic_len :]

    try:
        payload_text = payload.decode("utf-8")
        payload_value = json.loads(payload_text)
    except Exception:
        payload_value = payload.decode("utf-8", errors="replace")

    return topic, payload_value


