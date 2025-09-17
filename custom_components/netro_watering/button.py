"""Support du bouton Refresh pour Netro Watering."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NetroControllerUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

NETRO_CONTROLLER_BUTTON_DESCRIPTION = ButtonEntityDescription(
    key="refresh",
    name="Refresh",
    entity_registry_enabled_default=True,
    translation_key="refresh",
    icon="mdi:refresh",
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the button platform."""
    controller: NetroControllerUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.info("Adding button entity for controller = %s", controller.device_name)

    async_add_entities(
        [NetroRefreshButton(controller, NETRO_CONTROLLER_BUTTON_DESCRIPTION)]
    )


class NetroRefreshButton(
    CoordinatorEntity[NetroControllerUpdateCoordinator], ButtonEntity
):
    """Bouton qui force un refresh du contrôleur Netro."""

    entity_description: ButtonEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NetroControllerUpdateCoordinator,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the Netro refresh button entity.

        Args:
            coordinator: The data update coordinator for Netro.
            description: The entity description for the button.
        """
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}-{description.key}"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Pressing the button requests an immediate update."""
        _LOGGER.debug(
            "Netro: refresh button pressed for %s", self.coordinator.serial_number
        )

        # Si ton coordinator expose une méthode spécifique (ex: refresh_controller()),
        # tu peux l'appeler ici avant/à la place du request_refresh.
        # await self.coordinator.refresh_controller()

        # Dans tous les cas, on (re)planifie une mise à jour via le DataUpdateCoordinator
        await self.coordinator.async_request_refresh()
