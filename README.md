[![Build Status](https://travis-ci.org/sarafanio/core-service.svg?branch=master)](https://travis-ci.org/sarafanio/core-service)
[![codecov](https://codecov.io/gh/sarafanio/core-service/branch/master/graph/badge.svg)](https://codecov.io/gh/sarafanio/core-service)
[![Documentation Status](https://readthedocs.org/projects/core-service/badge/?version=latest)](https://core-service.readthedocs.io/en/latest/?badge=master)

core-service
============

`core-service` is a package aimed to provide a simple wrapper for asynchronous service.

Features:

* simple start/stop asynchronous Service interface
* nested services
* simple service orchestration
* service-bound asyncio tasks management
* 100% test coverage

Install:

```shell script
pip install -U core-service
```

Quick example:

```python
from asyncio import run, sleep
from core_service import Service, task

class MyService(Service):
    @task(workers=10)
    async def my_heavy_task(self):
        await sleep(1)
        print("Heavy task performed")

async def main():
    service = MyService()
    await service.start()
    await sleep(10)
    await service.stop()

run(main())
```

[Read the docs](https://core-service.readthedocs.io/en/master/).

You can support project development by staring it on github.

You can also donate ETH to our address:

    0x957D0b2E4afA74A49bbEa4d7333D13c0b11af60F
