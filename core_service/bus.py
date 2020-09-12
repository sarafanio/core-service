import abc
import asyncio
import inspect
from collections import defaultdict
from functools import wraps
from typing import Optional, Dict, List

from core_service.abstract import AbstractService
from core_service.exceptions import UnhealthyException


def fullname(o):
    cls = o if isinstance(o, type) else o.__class__
    return cls.__module__ + '.' + cls.__name__


class ServiceBus:
    """Service-bus.

    Used for communication between services.

    Subscribers can subscribe to one or more object types and
    publishers can emmit such an object.
    """
    #: mapping of emitted object types to a list of subscribers queues
    _subscriptions = Dict[str, List[asyncio.Queue]]

    def __init__(self):
        self._subscriptions = defaultdict(list)

    def subscribe(self, *obj_types):
        queue = asyncio.Queue()
        for obj_type in obj_types:
            self._subscriptions[fullname(obj_type)].append(queue)
        return queue

    async def emit(self, obj):
        obj_type_name = fullname(obj)
        for receiver in self._subscriptions[obj_type_name]:
            await receiver.put(obj)


class ServiceBusMixin(AbstractService, abc.ABC):

    """Service mixin with bus functionality.

    Allows to use `listener()` decorator on methods.
    """

    bus: Optional[ServiceBus] = None
    _bus_queue: Optional[asyncio.Queue] = None
    _bus_listeners: Dict[str, List]
    _bus_reader: asyncio.Task

    def set_service_bus(self, bus: Optional[ServiceBus] = None):
        """Set and init service bus for this service instance."""
        if bus is None:
            bus = ServiceBus()
        self.bus = bus
        self._bus_listeners = defaultdict(list)
        members = inspect.getmembers(self, predicate=inspect.isroutine)
        subscriptions = set()
        for name, method in members:
            if hasattr(method, "bus_handler_types"):
                self.log.debug("Found handler for %s objects", method.bus_handler_types)
                for obj_type in method.bus_handler_types:
                    subscriptions.add(obj_type)
                    self._bus_listeners[fullname(obj_type)].append(method)
                    self.log.info("Subscribe %s for %s", self, fullname(obj_type))
        self._bus_queue = bus.subscribe(*subscriptions)

    async def emit(self, obj):
        """Place some object on service-bus."""
        if self.bus is None:  # pragma: no cover
            raise RuntimeError("Service bus is not initialized on %s" % self)
        await self.bus.emit(obj)

    async def start_bus_reader(self):
        self.log.debug("Starting bus reader task")
        self._bus_reader = self.loop.create_task(self._bus_reader_task())

    async def stop_bus_reader(self):
        self.log.debug("Stop bus reader task")
        self._bus_reader.cancel()
        try:
            await self._bus_reader
        except asyncio.CancelledError:
            pass
        except:  # noqa
            self.log.exception("Exception from the bus reader task")

    async def _bus_reader_task(self):
        """Read objects from the bus and pass them to dispatch method one by one."""
        try:
            while not self.should_stop:
                if self.bus is None:  # pragma: no cover
                    raise RuntimeError("Service bus is not initialized on %s" % self)
                self.log.debug("Wait for bus message")
                try:
                    obj = await self._bus_queue.get()
                except RuntimeError:  # pragma: no cover
                    self.log.debug("Can't read from bus queue, looks like loop closed")
                    break

                self.log.debug("Object from bus received: %s", obj)
                try:
                    await self.dispatch(obj)
                except asyncio.CancelledError:  # pragma: no cover
                    raise
                self._bus_queue.task_done()
        except asyncio.CancelledError:  # pragma: no cover
            pass

    async def dispatch(self, obj):
        """Dispatch object from the service-bus on current service"""
        obj_type_name = fullname(obj)
        self.log.debug("Dispatching %s %s", obj_type_name, obj)
        for listener in self._bus_listeners[obj_type_name]:
            try:
                await listener(obj)
            except Exception:  # noqa
                self.log.exception("Exception while processing bus object %s by handler %s",
                                   obj, listener)

    async def healthcheck(self):
        await super().healthcheck()
        try:
            if self._bus_reader.done():  # pragma: no cover
                e = self._bus_reader.exception()
                if e:
                    raise e
                self.log.debug("Task %s was cancelled", self._bus_reader)
        except asyncio.CancelledError:  # pragma: no cover
            pass
        except Exception as e:  # pragma: no cover
            self.log.exception("Service tasks healthcheck failed with exception")
            raise UnhealthyException from e
