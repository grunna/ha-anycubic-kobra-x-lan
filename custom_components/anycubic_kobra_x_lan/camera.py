"""Printer camera served from the printer's local HTTP-FLV endpoint.

The printer only pushes video after it has been sent ``startCapture`` over
MQTT, and it forgets that after every reboot. Home Assistant therefore has to
ask for the stream each time it opens it, otherwise the entity stays idle with
no picture.

The Kobra X answers the FLV request with ``206 Partial Content`` which
ffmpeg/go2rtc refuse, so the stream is relayed through a small Home Assistant
view that answers ``200`` instead (same approach as Nino6689/hass-anycubic).
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from http import HTTPStatus
from typing import Any
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientTimeout, hdrs, web

from homeassistant.components.camera import (
    Camera,
    CameraEntityFeature,
    CameraView,
)
from homeassistant.components.camera.const import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator

_LOGGER = logging.getLogger(__name__)

_STREAM_PROXY_URL = "/api/anycubic_kobra_x_lan/camera_stream/{entity_id}"
_STREAM_CHUNK_SIZE = 64 * 1024
_STREAM_CONNECT_TIMEOUT = 10
# A running capture sends data many times a second.
_STREAM_FIRST_DATA_TIMEOUT = 8
_STREAM_READ_TIMEOUT = 20
_VIEW_REGISTERED = f"{DOMAIN}_camera_view_registered"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    if not hass.data.get(_VIEW_REGISTERED):
        hass.http.register_view(
            AnycubicKobraXLanCameraStreamView(hass.data[DATA_COMPONENT])
        )
        hass.data[_VIEW_REGISTERED] = True

    async_add_entities([AnycubicKobraXLanCamera(coordinator, entry)])


class AnycubicKobraXLanCamera(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    Camera,
):
    # Without STREAM Home Assistant never calls stream_source and the camera
    # just sits idle.
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
    ) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)

        self._entry = entry
        self._stream_proxy_token = secrets.token_urlsafe(32)
        self._attr_unique_id = f"{entry.entry_id}_camera"
        # Stable key so dashboards/cards can find the entity whatever its name.
        self._attr_translation_key = "camera"
        self._attr_has_entity_name = True
        self._attr_name = "Camera"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
        }

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.camera_stream_url() is not None

    @property
    def is_on(self) -> bool:
        peripherie = _payload(self.coordinator.data or {}, "peripherie")
        # Before the first peripherie report assume the camera is there.
        return bool(peripherie.get("camera", True))

    @property
    def is_streaming(self) -> bool:
        camera_stream = (self.coordinator.data or {}).get("camera_stream")
        return isinstance(camera_stream, dict) and bool(camera_stream.get("enabled"))

    @property
    def use_stream_for_stills(self) -> bool:
        # The printer has no snapshot endpoint; stills come out of the stream
        # Home Assistant already holds instead of opening a second one.
        return True

    async def stream_source(self) -> str | None:
        if not self.is_on:
            return None

        stream_url = self.coordinator.camera_stream_url()

        if not stream_url:
            return None

        await self.coordinator.async_start_camera()

        if not _is_local_flv(stream_url) or self.entity_id is None:
            return stream_url

        try:
            base_url = get_url(
                self.hass,
                allow_external=False,
                prefer_external=False,
            ).rstrip("/")
        except NoURLAvailableError:
            return stream_url

        path = _STREAM_PROXY_URL.format(entity_id=self.entity_id)
        return f"{base_url}{path}?token={self._stream_proxy_token}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        camera_stream = (self.coordinator.data or {}).get("camera_stream")

        attrs: dict[str, Any] = {
            "camera_available": self.is_on,
        }

        if isinstance(camera_stream, dict):
            attrs["stream_enabled"] = camera_stream.get("enabled")
            attrs["last_stream_action"] = camera_stream.get("last_action")
            attrs["last_stream_state"] = camera_stream.get("last_state")
            attrs["last_stream_code"] = camera_stream.get("last_code")

        return attrs


class AnycubicKobraXLanCameraStreamView(CameraView):
    """Relay the printer's HTTP-FLV stream with a 200 instead of a 206."""

    url = _STREAM_PROXY_URL
    name = "api:anycubic_kobra_x_lan:camera_stream"

    async def get(
        self,
        request: web.Request,
        entity_id: str,
    ) -> web.StreamResponse:
        camera = self.component.get_entity(entity_id)

        if not isinstance(camera, AnycubicKobraXLanCamera):
            raise web.HTTPNotFound

        token = request.query.get("token", "")

        if not secrets.compare_digest(token, camera._stream_proxy_token):
            raise web.HTTPForbidden

        if not camera.is_on:
            raise web.HTTPServiceUnavailable

        return await self.handle(request, camera)

    async def handle(
        self,
        request: web.Request,
        camera: Camera,
    ) -> web.StreamResponse:
        if not isinstance(camera, AnycubicKobraXLanCamera):
            raise web.HTTPNotFound

        source_url = camera.coordinator.camera_stream_url()

        if source_url is None:
            raise web.HTTPServiceUnavailable

        await camera.coordinator.async_start_camera()
        upstream, first = await _async_open_upstream(camera, source_url)

        if upstream is None:
            # The printer is not pushing although we think it is (it stopped
            # on its own, or the last start was lost): restart it once.
            _LOGGER.debug("Camera sent no video, restarting the capture")
            await camera.coordinator.async_start_camera(force=True)
            await asyncio.sleep(2)
            upstream, first = await _async_open_upstream(camera, source_url)

        if upstream is None:
            raise web.HTTPBadGateway(reason="The printer camera sends no video")

        try:
            response = web.StreamResponse(
                status=HTTPStatus.OK,
                headers={
                    hdrs.CONTENT_TYPE: upstream.headers.get(
                        hdrs.CONTENT_TYPE,
                        "video/x-flv",
                    ),
                    hdrs.CACHE_CONTROL: "no-store",
                },
            )
            await response.prepare(request)

            try:
                await response.write(first)

                while True:
                    chunk = await asyncio.wait_for(
                        upstream.content.read(_STREAM_CHUNK_SIZE),
                        _STREAM_READ_TIMEOUT,
                    )

                    if not chunk:
                        break

                    await response.write(chunk)

                await response.write_eof()
            except TimeoutError:
                # The printer stopped pushing: the next open restarts it.
                _LOGGER.debug("Camera stream stalled, capture marked stopped")
                camera.coordinator.async_camera_stalled()
            except (ClientError, ConnectionResetError) as err:
                # Viewer went away or the printer stopped pushing; the stream
                # worker reconnects and the next open restarts the capture.
                _LOGGER.debug("Camera stream relay ended: %s", err)

            return response
        finally:
            upstream.release()


async def _async_open_upstream(camera, source_url: str):
    """Connect to the printer and wait for the first bytes of video.

    Returns (response, first_chunk), or (None, b"") when the printer refuses
    or stays silent, so the caller can restart the capture.
    """
    try:
        upstream = await async_get_clientsession(camera.hass).get(
            source_url,
            timeout=ClientTimeout(
                total=None,
                sock_connect=_STREAM_CONNECT_TIMEOUT,
                sock_read=None,
            ),
        )
    except (ClientError, TimeoutError) as err:
        _LOGGER.debug("Could not connect to the printer camera: %s", err)
        return None, b""

    if upstream.status not in (HTTPStatus.OK, HTTPStatus.PARTIAL_CONTENT):
        _LOGGER.debug("Printer camera returned HTTP %s", upstream.status)
        upstream.release()
        return None, b""

    try:
        first = await asyncio.wait_for(
            upstream.content.read(_STREAM_CHUNK_SIZE),
            _STREAM_FIRST_DATA_TIMEOUT,
        )
    except (ClientError, TimeoutError) as err:
        _LOGGER.debug("Printer camera sent no data: %s", err)
        upstream.release()
        return None, b""

    if not first:
        upstream.release()
        return None, b""

    return upstream, first


def _is_local_flv(url: str) -> bool:
    try:
        return urlsplit(url).scheme == "http"
    except ValueError:
        return False


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report
