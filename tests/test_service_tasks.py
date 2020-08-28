import pytest
import asyncio

from core_service import Service, task


@pytest.mark.asyncio
async def test_service_task_simple():
    class TestTaskService(Service):
        example_task_counter = 0

        @task(sleep_interval=0.1)
        async def example_task(self):
            self.example_task_counter += 1

    service = TestTaskService()
    await service.start()
    await asyncio.sleep(0)
    assert len(service._tasks.tasks) == 1
    await service.stop()
    assert service.example_task_counter > 0


@pytest.mark.asyncio
async def test_non_periodic_task():
    """Test non-periodic task run only once.
    """
    class TestTaskService(Service):
        example_task_counter = 0

        @task(sleep_interval=0.1, periodic=False)
        async def example_task(self):
            self.example_task_counter += 1

    service = TestTaskService()
    await service.start()
    await asyncio.sleep(0)
    await service.stop()
    assert service.example_task_counter == 1


@pytest.mark.asyncio
async def test_service_task_with_exception():
    """Test failed task triggering service fail state.
    """
    class FailTaskService(Service):
        @task()
        async def example_fail_task(self):
            raise Exception("Fail for example")

    service = FailTaskService()
    await service.start()
    await asyncio.sleep(0)

    assert service.running is False

    await service.stop()
