import asyncio
from dataclasses import dataclass

import pytest

from core_service import Service
from core_service.bus import ServiceBusMixin, ServiceBus
from core_service.decorators import listener


@dataclass
class A:
    a: int = 1


@dataclass
class B:
    b: int = 2


class TestServiceA(Service):
    counter = 0

    @listener(A)
    async def listen_a(self, obj):
        self.log.info("Task A received %s", obj)
        self.counter += 1
        await self.emit(B())


class TestServiceB(Service):
    counter = 0
    counter_2 = 0

    @listener(B)
    async def listen_b(self, obj):
        self.log.info("Task B received %s in listen_b", obj)
        self.counter += 1

    @listener(B)
    async def listen_b_2(self, obj):
        self.log.info("Task B received %s in listen_b_2", obj)
        self.counter_2 += 1


@pytest.mark.asyncio
async def test_create_bus():
    TestServiceA()


@pytest.mark.asyncio
async def test_service_bus():
    bus = ServiceBus()
    a = TestServiceA(bus=bus)
    b = TestServiceB(bus=bus)
    try:
        await a.start()
        await b.start()
        await a.emit(A())
        await b.emit(B())
        await asyncio.sleep(1)
        assert a.counter == 1
        assert b.counter == 2
        assert b.counter_2 == 2
    finally:
        await a.stop()
        await b.stop()


@pytest.mark.asyncio
async def test_failed_handler(caplog):
    class TestService(Service):
        @listener(A)
        async def handler(self, obj):
            raise Exception("EXPECTED_EXCEPTION")

    service = TestService()
    await service.start()
    try:
        await service.emit(A())
        await asyncio.sleep(0)
        assert service.running is True
        assert 'EXPECTED_EXCEPTION' in caplog.text
        assert 'Exception while processing bus object A(a=1)' in caplog.text
    finally:
        await service.stop()
    await asyncio.get_event_loop().shutdown_asyncgens()
