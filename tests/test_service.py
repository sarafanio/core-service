import pytest

from core_service import Service


class TestService(Service):
    pass


@pytest.mark.asyncio
async def test_simple(event_loop):
    service = TestService(loop=event_loop)
    await service.start()
    await service.stop()


@pytest.mark.asyncio
async def test_unantended_deletion():
    service = TestService()
    await service.start()
    with pytest.raises(RuntimeError):
        service.__del__()
    await service.stop()
