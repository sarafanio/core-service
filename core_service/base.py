import asyncio
from typing import Optional

from .abstract import AbstractService
from .container import ServiceContainerMixin
from .exceptions import ServiceStartupException, UnhealthyException
from .tasks import TasksMixin


class Service(ServiceContainerMixin, TasksMixin, AbstractService):
    """Base service class.

    Your services should be inherited from this class.

    Service class provides a basic asynchronous service lifecycle methods.
    You should extend it for your needs.
    """
    _monitoring_task: Optional[asyncio.Task] = None
    #: interval in seconds to sleep between healthcheck runs
    _monitoring_interval: float = .1

    def __init__(self, *, loop=None, monitoring_interval: float = .1):
        self._loop = loop
        self._monitoring_interval = monitoring_interval
        super().__init__()

    async def start(self):
        """Start service.

        Set `running` flag to `True`, start service tasks, nested services
        and create monitoring task.

        You can override this method in your service implementation to apply custom
        start logic. But don't forget to invoke super implementation.
        """
        self.log.debug("Starting")
        self.running = True
        await self._start_service_tasks()
        try:
            await self._start_nested_services()
        except (ServiceStartupException, TypeError):
            self.log.exception("Failed to start nested service")
            self.running = False
            self.should_stop = True
            await self._stop_service_tasks()
            raise
        self._monitoring_task = self.loop.create_task(self.monitoring_task(),
                                                      name=f"{self.name}.monitoring_task")
        self.log.info("Service was started")

    async def stop(self):
        """Stop service.

        Set `should_stop` flag to `True`, `running` to `False` and start shutdown sequence.

        Nested services will be stopped first, service tasks will be cancelled than.

        You can override this method in your service implementation to apply custom
        start logic. But don't forget to invoke super implementation.
        """
        self.should_stop = True
        self.running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        await self._stop_nested_services()
        await self._stop_service_tasks()

    async def monitoring_task(self):
        """Monitoring task.

        Started with a service. Run healthcheck periodically and force service
        to stop if it failed.
        """
        while not self.should_stop:
            try:
                await self.healthcheck()
            except UnhealthyException:
                self.log.exception("Healthcheck failed with exception")
                break
            except Exception:  # noqa
                self.log.exception("Service healthcheck failed with unexpected exception")
                break
            await asyncio.sleep(self._monitoring_interval)
        # terminate service on exit
        if not self.should_stop:
            await self.stop()
