import pytest
import asyncio

from core_service import Service, task


class TestTaskService(Service):
    example_task_counter = 0

    @task(sleep_interval=0.1)
    async def example_task(self):
        self.example_task_counter += 1


@pytest.mark.asyncio
async def test_service_task_simple():
    service = TestTaskService()
    await service.start()
    await asyncio.sleep(0)
    assert len(service._tasks.tasks) == 1
    await service.stop()
    assert service.example_task_counter > 0


@pytest.mark.asyncio
async def test_service_task_with_exception():
    class FailTaskService(Service):
        @task()
        async def example_fail_task(self):
            raise Exception("Fail for example")

    service = FailTaskService()
    await service.start()
    await asyncio.sleep(0)

    assert service.running is False

    await service.stop()
