import asyncio

import pytest

from core_service import Service, requirements, task
from core_service.exceptions import ServiceStartupException


class NestedService(Service):
    pass


class MainService(Service):
    def __init__(self, *, nested=None, loop=None):
        super().__init__(loop=loop)
        if nested is None:
            nested = NestedService
        self.nested = nested(loop=loop)

    @requirements()
    async def main_requirements(self):
        return [
            self.nested
        ]


@pytest.mark.asyncio
async def test_nested_service_lifecycle():

    service = MainService()

    await service.start()
    assert service.running
    assert service.nested.running

    await service.stop()
    assert not service.running
    assert not service.nested.running


@pytest.mark.asyncio
async def test_nested_service_startup_failure():
    class FailStartupService(Service):
        async def start(self):
            raise Exception("Example startup exception")

    service = MainService(nested=FailStartupService)
    with pytest.raises(ServiceStartupException):
        await service.start()


@pytest.mark.asyncio
async def test_nested_service_silent_startup_failure():
    class FailOnStartupService(Service):
        async def start(self):
            await super().start()
            self.running = False

    service = MainService(nested=FailOnStartupService)
    with pytest.raises(ServiceStartupException):
        await service.start()


@pytest.mark.asyncio
async def test_nested_service_task_failure():
    class FailService(Service):
        @task()
        async def fail_task(self):
            raise Exception

    service = MainService(nested=FailService)
    await service.start()
    await asyncio.sleep(0)
    assert not service.running
    assert not service.nested.running
    await service.stop()


@pytest.mark.asyncio
async def test_nested_service_stop_failure():
    class FailOnStopService(Service):
        async def stop(self):
            await super().stop()
            raise Exception("Example stop exception")

    service = MainService(nested=FailOnStopService)
    await service.start()
    await service.stop()
    # TODO: check log contains exception


@pytest.mark.asyncio
async def test_broken_healthcheck():
    """Healthcheck method of nested service is broken.

    ServiceStartupException should be raised on `start()`.
    """
    class BrokenHealthcheckService(Service):
        async def healthcheck(self):
            raise Exception("Broken healthcheck for testing")

    service = MainService(nested=BrokenHealthcheckService)
    with pytest.raises(ServiceStartupException):
        await service.start()


@pytest.mark.asyncio
async def test_nested_service_relation():
    class RequiredService(Service):
        pass

    class DependentService(Service):
        def __init__(self, *, required_service, loop=None):
            super().__init__(loop=loop)
            self.required_service = required_service

        async def start(self):
            if self.required_service.running is False:
                raise RuntimeError("RequiredService is not running")
            await super().start()

    class MainWiredService(Service):
        def __init__(self):
            super().__init__()
            self.required_service = RequiredService()

        @requirements('main_requirements')
        async def a_secondary_requirements(self):  # `a_` is used to became first
            return [
                DependentService(required_service=self.required_service)
            ]

        @requirements()
        async def main_requirements(self):
            return [
                self.required_service
            ]

        @requirements('main_requirements', 'a_secondary_requirements')
        async def third_party_requirements(self):
            return []

    service = MainWiredService()
    await service.start()
    await service.stop()


@pytest.mark.asyncio
async def test_wrong_requirements_output():
    class WrongRequirementsService(Service):
        @requirements()
        async def wrong_requirements_service(self):
            return 1

    service = WrongRequirementsService()
    with pytest.raises(TypeError):
        await service.start()


@pytest.mark.asyncio
async def test_unresolvable_requirements():
    class UnresolvableService(Service):
        @requirements('second_reqs')
        async def first_reqs(self):
            return []

        @requirements('first_reqs')
        async def second_reqs(self):
            return []

    service = UnresolvableService()
    with pytest.raises(RuntimeError):
        await service.start()
