"""Renders of the running job, as the printer answers file/fileDetails."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator
from .entity import AnycubicKobraXLanEntity

IMAGES = {
    "thumbnail": ("print_preview", "Print preview"),
    "plate": ("print_plate", "Print plate view"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AnycubicKobraXLanPreviewImage(hass, coordinator, entry, image, key, name)
        for image, (key, name) in IMAGES.items()
    )


class AnycubicKobraXLanPreviewImage(AnycubicKobraXLanEntity, ImageEntity):
    """Unavailable until the printer sends the job's renders."""

    _attr_content_type = "image/png"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        image: str,
        key: str,
        name: str,
    ) -> None:
        AnycubicKobraXLanEntity.__init__(self, coordinator, entry, key)
        ImageEntity.__init__(self, hass)
        self._image = image
        self._attr_name = name

    @property
    def available(self) -> bool:
        return super().available and self._image in self.coordinator.print_previews

    @property
    def image_last_updated(self):
        return self.coordinator.print_preview_updated

    @property
    def extra_state_attributes(self):
        return {"filename": self.coordinator.print_preview_filename}

    async def async_image(self) -> bytes | None:
        return self.coordinator.print_previews.get(self._image)
