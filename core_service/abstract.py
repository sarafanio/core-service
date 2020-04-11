import abc
import asyncio
import logging
from typing import Optional

from .exceptions import UnhealthyException
from .logging import ServiceLoggerAdapter


class AbstractService(abc.ABC):
    running: bool = False
    should_stop: bool = False

    _loop: Optional[asyncio.AbstractEventLoop] = None
    _log: Optional[ServiceLoggerAdapter] = None

    @property
    def loop(self):
        """Event loop
        """
        if not self._loop:
            self._loop = asyncio.get_event_loop()
        return self._loop

    @property
    def name(self):
        """Service name.

        Default implementation return class name.

        Used in log output etc. Should include unique identifiers.
        """
        return self.__class__.__name__

    @property
    def log(self):
        """Service logger with service name under the `service` key of extra
        """
        if self._log is None:
            logger = logging.getLogger(self.__class__.__module__)
            self._log = ServiceLoggerAdapter(logger, extra={'service': self.name})
        return self._log

    @abc.abstractmethod
    async def start(self):
        """Asynchronous start method.
        """
        pass  # pragma: nocover

    @abc.abstractmethod
    async def stop(self):
        """Asynchronous stop method.

        Service should gracefully finish all its activity.
        """
        pass  # pragma: nocover

    async def healthcheck(self):
        """Healthcheck method.

        This method can be invoked to check if service is healthy and running.
        Should raise :py:class:`core_service.exceptions.UnhealthyException`
        if it is not healthy.

        Default implementation checks that `running` flag is `True`. You can overload
        this method to add additional checks.
        """
        if not self.running:
            raise UnhealthyException

    def __del__(self):
        if self.running:
            raise RuntimeError("Service %s is not stopped correctly" % self.name)
