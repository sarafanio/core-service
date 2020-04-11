import asyncio

import pytest

from core_service.tasks import TasksCollection


async def example_task():
    return True


@pytest.mark.asyncio
async def test_finished_task_removed(event_loop):
    collection = TasksCollection()
    collection.add(event_loop.create_task(example_task()))
    await asyncio.sleep(0)
    collection.check_all()
    assert len(collection.tasks) == 0
