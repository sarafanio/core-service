"""Tasks container.
"""
import abc
import asyncio
import inspect
import logging
from typing import Awaitable, Callable, List

from .abstract import AbstractService
from .exceptions import UnexpectedTaskException, UnhealthyException

log = logging.getLogger(__name__)


class ServiceTask:
    """Service task wrapper.

    Wraps service task async method. Contains task execution parameters.
    """
    service: AbstractService
    #: task will be executed in infinity loop with sleep_interval between runs
    periodic: bool = True
    #: number of seconds between task executions
    sleep_interval: float = .1
    #: number of task instances running in parallel
    workers: int = 1

    def __init__(self,
                 service: AbstractService,
                 f: Callable[[], Awaitable],
                 periodic: bool = True,
                 sleep_interval: float = .1,
                 workers: int = 1):
        self.callable = f
        self.service = service
        self.periodic = periodic
        self.sleep_interval = sleep_interval
        self.workers = workers

    async def run(self):
        """Run task.
        """
        while not self.service.should_stop:
            await self.callable()
            await asyncio.sleep(self.sleep_interval)


class TasksCollection:
    tasks: List[asyncio.Task]

    def __init__(self):
        self.tasks = []

    def add(self, task: asyncio.Task):
        """Add task with definition to collection.
        """
        self.tasks.append(task)

    def check_all(self):
        """Check tasks health.

        Remove finished tasks from collection.

        Raise exception if some task failed and `allow_fail` is set to `False` for it.
        """
        for task in self.tasks:
            if task.done():
                log.debug("Task %s is done", task)
                try:
                    e = task.exception()
                    if e:
                        raise e
                except asyncio.CancelledError:  # pragma: nocover
                    log.debug("Task %s was cancelled", task)
                except Exception as e:  # noqa
                    raise UnexpectedTaskException() from e
                self.tasks.remove(task)
                log.debug("Remove finished task %s from collection", task)

    async def stop_all(self, raise_exceptions=False):
        """Stop all tasks in collection.

        Cancel all tasks. Will raise exceptions if `raise_exceptions` is `True`
        or log exception instead.
        """
        task_list = []
        for task in self.tasks:
            task.cancel()
            task_list.append(task)
        results = await asyncio.gather(*task_list, return_exceptions=not raise_exceptions)
        # log exceptions if not raised
        if not raise_exceptions:
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    task = self.tasks[i]
                    try:
                        raise r
                    except asyncio.CancelledError:  # pragma: nocover
                        log.debug("Task %s was cancelled", task)
                    except Exception:  # noqa
                        log.exception("Task %s stopped with exception",
                                      task.get_name())
        log.debug("Cancelled %i service tasks", len(self.tasks))


class TasksMixin(AbstractService, abc.ABC):
    """Tasks mixin for BaseService.
    """
    _tasks: TasksCollection

    def __init__(self):
        super().__init__()
        self._tasks = TasksCollection()

    async def healthcheck(self):
        await super().healthcheck()
        try:
            self._tasks.check_all()
        except UnexpectedTaskException as e:
            self.log.exception("Service tasks healthcheck failed with exception")
            raise UnhealthyException from e

    async def _start_service_tasks(self):
        """Start tasks defined on the service.
        """
        members = inspect.getmembers(self, predicate=inspect.isroutine)
        for name, method in members:
            if hasattr(method, "service_task"):
                self.log.debug("Service task %s found", method)
                service_task = ServiceTask(self, method, **method.service_task_definition)
                for i in range(service_task.workers):
                    task_name = ".".join([self.name, method.__name__, str(i)])
                    log.debug("Create task %s", task_name)
                    task = self.loop.create_task(service_task.run(), name=task_name)
                    self._tasks.add(task)

    async def _stop_service_tasks(self):
        """Cancel and await all managed service tasks.
        """
        await self._tasks.stop_all()
