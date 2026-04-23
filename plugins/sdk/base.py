"""Plugin SDK base interfaces for OpenMythos plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PluginContext:
    """Runtime context passed to plugin implementations."""

    request_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


class PluginBase(ABC):
    """Common plugin interface used by lightweight plugin implementations."""

    plugin_id: str = ""
    version: str = ""

    @abstractmethod
    def run(self, payload: dict[str, Any], context: PluginContext | None = None) -> dict[str, Any]:
        """Execute plugin behavior against a structured payload."""


class CapabilityPlugin(PluginBase):
    """Plugin base class for capability-driven behavior dispatch."""

    capabilities: tuple[str, ...] = ()

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities
