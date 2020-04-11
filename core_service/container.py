"""Service container.

Any service can contain other services. Nested services will be started
and stopped together.
"""
import abc
import inspect
import logging
from typing import List

from .abstract import AbstractService
from .exceptions import ServiceStartupException

log = logging.getLogger(__name__)


class ServiceCollection:
    """Collection of services.

    Services in collection can be started, stopped and checked together
    with appropriate methods.

    Services are started in direct order and stopped in backward. Only
    already started services will be stopped if some of the service startup
    failed.
    """
    services: List[AbstractService]
    started_services: List[AbstractService]

    def __init__(self):
        self.services = []
        self.started_services = []

    def add(self, service: AbstractService):
        """Add service to collection.
        """
        self.services.append(service)

    async def healthcheck(self):
        """Check health of all services in collection.
        """
        for service in self.services:
            await service.healthcheck()

    async def start_all(self):
        """Start all services or rollback on failure.

        Services will be started in order they were added.
        """
        try:
            for service in self.services:
                try:
                    await service.start()
                    await service.healthcheck()
                except Exception as e:
                    log.exception("Exception while starting %s service", service)
                    raise ServiceStartupException from e
                self.started_services.append(service)
        except ServiceStartupException:
            log.error("Stopping services on startup failure")
            await self.stop_all()
            raise

    async def stop_all(self):
        """Stop all services in collection.

        Only started services will be stopped. Services will be stopped
        in reverse to startup order.
        """
        log.debug("Stopping nested services.")
        for service in reversed(self.started_services):
            try:
                await service.stop()
            except Exception:  # noqa
                log.exception("Fail to stop %s service.", service)
        else:
            log.debug("There are no services to stop.")
        log.debug("All nested services were stopped.")


class ServiceContainerMixin(AbstractService, abc.ABC):
    """Service container mixin.

    Add service collection and related functionality to BaseService.
    """
    _services: ServiceCollection

    def __init__(self):
        self._services = ServiceCollection()
        super().__init__()

    async def healthcheck(self):
        await super().healthcheck()
        await self._services.healthcheck()

    async def _start_nested_services(self):
        """Start nested services.

        Underlying collection will be filled.

        Startup order depend on the requirement method name defined on Service class
        and the defined dependencies.

        :raise RuntimeError: if startup order can't be resolved
        """
        loaded = set()
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        ordering_required = [name for name, method in members
                             if hasattr(method, "requirements_definition")]
        self.log.debug("Requirements will be gathered from %s",
                       ', '.join(ordering_required))
        while ordering_required:
            ordered_count = 0
            for name in ordering_required[:]:
                self.log.debug("Check %s", name)
                method = getattr(self, name)
                requirements = getattr(method, "service_requirements")
                if len(requirements) > 0 and not loaded.issuperset(requirements):
                    self.log.debug("Not enought requirements. Loaded: %s, Required: %s",
                                   loaded, requirements)
                    continue
                self.log.debug("Getting requirements from %s", name)
                services = await method()
                self.log.debug("Requirements from %s: %s", method, services)
                if not (services is None or isinstance(services, list)):
                    raise TypeError("Requirements method must return list or None. "
                                    "It returns %s (%s type) instead.",
                                    services, type(services))
                if services:
                    for service in services:
                        self._services.add(service)
                ordering_required.remove(name)
                ordered_count += 1
                loaded.add(name)
                self.log.debug("Nested service %s was loaded", name)
            if ordered_count == 0:
                raise RuntimeError(
                    "Can't resolve services dependencies "
                    "from %s" % ', '.join(ordering_required)
                )

        await self._services.start_all()

    async def _stop_nested_services(self):
        """Stop nested services in reverse order.
        """
        await self._services.stop_all()
