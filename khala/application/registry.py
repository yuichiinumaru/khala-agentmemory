"""Service Registry for Modular Component Architecture.

Implements Strategy 45: Modular Component Architecture.
Allows dynamic registration and retrieval of services (plugins).
"""

import logging
from typing import Dict, Any, Type, Optional, Callable

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """
    Central registry for application services.
    Supports singleton instance management and factory-based creation.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
            cls._instance._services = {}
            cls._instance._factories = {}
        return cls._instance

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            cls = ServiceRegistry()
        return cls._instance

    def register(self, name: str, service: Any):
        """Register an instantiated service."""
        if name in self._services:
            logger.warning(f"Overwriting existing service: {name}")
        self._services[name] = service
        logger.debug(f"Registered service: {name}")

    def register_factory(self, name: str, factory: Callable[[], Any]):
        """Register a factory function for a service."""
        self._factories[name] = factory
        logger.debug(f"Registered factory for: {name}")

    def get(self, name: str) -> Optional[Any]:
        """Get a service by name."""
        # Check instances first
        if name in self._services:
            return self._services[name]

        # Check factories
        if name in self._factories:
            try:
                instance = self._factories[name]()
                # Cache the instance? For now, let's assume factories produce singletons
                # or we want a new one each time.
                # If we want singletons, the factory should manage that or we cache here.
                # Let's cache here for "lazy singleton" behavior if it's not already registered.
                self._services[name] = instance
                return instance
            except Exception as e:
                logger.error(f"Failed to create service {name} from factory: {e}")
                return None

        logger.warning(f"Service not found: {name}")
        return None

    def list_services(self) -> Dict[str, str]:
        """List all registered services."""
        return {
            "instances": list(self._services.keys()),
            "factories": list(self._factories.keys())
        }

    def clear(self):
        """Clear the registry (useful for testing)."""
        self._services = {}
        self._factories = {}

# Global accessor
registry = ServiceRegistry()
