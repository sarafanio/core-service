Advanced example
================

When you know how to write and work with :py:class:`Service <core_service.Service>`,
you will need to know how to organize the whole application with a services.

Application is a service:

* it needs async start and stop
* it contains nested services

That's it, we can just subclass our `Application` from :py:class:`core_service.Service`:

.. code-block:: python

    from core_service import Service

    class Application(Service):
        pass

Logging
-------

`core-service` doesn't force you to use logging but you will always have `log` property
on any :py:class:`core_service.Service` instance. It will be
a :py:class:`logging.LoggerAdaper` instance with extra `service` key. You can use extra key
for log record filtering. Also this adapter prepends service name in square brackets before
each emitted log message.

Module of your service class will be always used as underlying logger name.
You can configure it using standard logging capabilities.

Configuration
-------------

`core-service` doesn't force the way you configure your application. But it is a common
practice to use

Web server
----------


Graceful shutdown.
------------------

Possibly, the main reason to have a root Application service is to handle the whole app shutdown.

We can implement
