"""
Service Registry for HuntEye Infrastructure (Dev 1.1).

Provides a centralized registry for discovering and accessing runtime services,
workers, and shared components. Enables loose coupling between modules.
"""

import threading
from typing import Dict, Any, Optional, Type, Callable
from core.logger import Logger


class ServiceRegistry:
    """
    Centralized service registry for HuntEye runtime.
    
    Services can be registered by name or type and retrieved later.
    Supports both singleton instances and factory functions.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._types: Dict[Type, str] = {}  # Maps type to service name
        self._lock = threading.RLock()
        
    def register_service(self, 
                        name: str, 
                        service: Any,
                        override: bool = False) -> bool:
        """
        Register a service instance.
        
        Args:
            name: Service name (unique identifier)
            service: Service instance to register
            override: Whether to override existing service
            
        Returns:
            True if service was registered successfully
        """
        with self._lock:
            if name in self._services and not override:
                Logger.warning(f"Service already registered | name={name}")
                return False
            
            self._services[name] = service
            service_type = type(service)
            self._types[service_type] = name
            Logger.info(f"Service registered | name={name} | type={service_type.__name__}")
            return True
    
    def register_factory(self, 
                        name: str, 
                        factory: Callable[[], Any],
                        override: bool = False) -> bool:
        """
        Register a factory function for creating service instances.
        
        Args:
            name: Service name (unique identifier)
            factory: Function that returns service instance
            override: Whether to override existing service/factory
            
        Returns:
            True if factory was registered successfully
        """
        with self._lock:
            if name in self._factories and not override:
                Logger.warning(f"Factory already registered | name={name}")
                return False
                
            self._factories[name] = factory
            Logger.info(f"Factory registered | name={name}")
            return True
    
    def get_service(self, name: str) -> Optional[Any]:
        """
        Get a service instance by name.
        
        Args:
            name: Service name
            
        Returns:
            Service instance or None if not found
        """
        with self._lock:
            # Check if we have a direct instance
            if name in self._services:
                return self._services[name]
            
            # Check if we have a factory
            if name in self._factories:
                factory = self._factories[name]
                try:
                    service = factory()
                    # Cache the created instance
                    self._services[name] = service
                    service_type = type(service)
                    self._types[service_type] = name
                    Logger.info(f"Service created from factory | name={name}")
                    return service
                except Exception as e:
                    Logger.error(f"Failed to create service from factory | name={name} | error={e}")
                    return None
            
            Logger.warning(f"Service not found | name={name}")
            return None
    
    def get_service_by_type(self, service_type: Type) -> Optional[Any]:
        """
        Get a service instance by its type.
        
        Args:
            service_type: Type of service to retrieve
            
        Returns:
            Service instance or None if not found
        """
        with self._lock:
            if service_type in self._types:
                name = self._types[service_type]
                return self.get_service(name)
            return None
    
    def unregister_service(self, name: str) -> bool:
        """
        Unregister a service by name.
        
        Args:
            name: Service name
            
        Returns:
            True if service was unregistered
        """
        with self._lock:
            removed = False
            if name in self._services:
                service = self._services.pop(name)
                service_type = type(service)
                if service_type in self._types:
                    del self._types[service_type]
                removed = True
                Logger.info(f"Service unregistered | name={name}")
            
            if name in self._factories:
                del self._factories[name]
                removed = True
                Logger.info(f"Factory unregistered | name={name}")
                
            return removed
    
    def list_services(self) -> Dict[str, str]:
        """
        List all registered services.
        
        Returns:
            Dictionary mapping service names to their types
        """
        with self._lock:
            result = {}
            for name, service in self._services.items():
                result[name] = type(service).__name__
            for name in self._factories:
                if name not in result:
                    result[name] = "factory"
            return result
    
    def clear(self):
        """Clear all registered services and factories."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._types.clear()
            Logger.info("Service registry cleared")


# Global service registry instance
_service_registry: Optional[ServiceRegistry] = None
_registry_lock = threading.RLock()


def get_service_registry() -> ServiceRegistry:
    """
    Get the global service registry instance.
    
    Returns:
        Global ServiceRegistry instance
    """
    global _service_registry
    with _registry_lock:
        if _service_registry is None:
            _service_registry = ServiceRegistry()
        return _service_registry


def register_service(name: str, service: Any, override: bool = False) -> bool:
    """
    Register a service instance with the global registry.
    """
    return get_service_registry().register_service(name, service, override)


def register_factory(name: str, factory: Callable[[], Any], override: bool = False) -> bool:
    """
    Register a factory function with the global registry.
    """
    return get_service_registry().register_factory(name, factory, override)


def get_service(name: str) -> Optional[Any]:
    """
    Get a service instance from the global registry.
    """
    return get_service_registry().get_service(name)


def get_service_by_type(service_type: Type) -> Optional[Any]:
    """
    Get a service instance by type from the global registry.
    """
    return get_service_registry().get_service_by_type(service_type)


def unregister_service(name: str) -> bool:
    """
    Unregister a service from the global registry.
    """
    return get_service_registry().unregister_service(name)


def list_services() -> Dict[str, str]:
    """
    List all services in the global registry.
    """
    return get_service_registry().list_services()