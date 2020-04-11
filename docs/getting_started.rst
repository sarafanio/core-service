Getting started
===============

To start using `core-service` you need to install it using pip:

.. code-block:: bash

    pip install -U core-service

Then you need to import :py:class:`core_service.Service` and subclass it first:

.. code-block:: python

    from core_service import Service

    class MyService(Service):
        pass

Such service can be started and stopped already:

.. code-block:: python

    import asyncio

    async def main():
        service = MyService()
        await service.start()
        await service.stop()

    asyncio.run(main())

You should always stop started service.

Service task
------------

There is a service task concept. Service task is a asyncio task that is managed by the service.
Example of such task may be a polling of data etc.

Failed task will fail the whole service.

Service task can be defined as an async method of Service class marked with
:py:meth:`core_service.task` decorator.

.. code-block:: python

    from core_service import Service, task


    class MyService(Service):
        @task(sleep_interval=1)
        async def my_task(self):
            self.log.info("my_task executed)

Task will be executed in infinite loop and will print log message every 1 sec.
Also, you can run multiple tasks in parallel by providing `workers` parameter greater
than 1. Sleeping interval will be applied to each instance individually.
See :py:meth:`core_service.task` reference for details.

Nested services
---------------

Service can contain multiple nested services inside. Such services will be started and stopped
with their parent. Failed service will fail his parent and all siblings too. Nested services will
be started after service tasks were running.

Nested services can be defined as async methods returning list of nested service instances
and wrapped with :py:meth:`core_service.requirements` decorator.

.. code-block:: python

    from core_service import Service, requirements

    class NestedService(Service):
        pass

    class MyService(Service):
        @requirements()
        async def nested_services(self):
            return [
                NestedService()
            ]

It is also possible to define dependencies for the requirements. It allows you to wait first
services to start before starting the next. Dependencies are defined as names of the other
methods wrapped with :py:meth:`core_service.requirements` decorator.

.. code-block:: python

    from core_service import Service, requirements

    class RequiredService(Service):
        pass

    class DependentService(Service):
        def __init__(self, required_service):
            self.required_service = required_service

        async def start(self):
            if not self.required_service.running:
                raise RuntimeError("Required service not running)
            await super().start()

    class MyService(Service):
        def __init__(self):
            super().__init__()
            self.required_service = RequiredService()

        @requirements()
        async def first_services():
            return [
                self.required_service
            ]

        @requirements('first_services')
        async def second_services():
            return [
                DependentService(self.required_service)
            ]

`DependentService` will be started only after `RequiredService` startup complete.
