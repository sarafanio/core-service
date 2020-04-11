from typing import List


def requirements(*deps: List[str]):
    """Decorator marking service method as a source of nested services list.

    Marked method should return a list of service instances that should be instantiated.

    Optional prop_name may contain name of object property with dependent service.
    Such method will be invoked only after attributes will be available, they will be a service
    and this service will be running.
    """
    def wrapper(f):
        f.requirements_definition = True
        f.service_requirements = deps
        return f

    return wrapper


def task(periodic: bool = True, sleep_interval: float = .1, workers: int = 1):
    """Decorator defining Service method as service task.

    Task will be started and stopped with a service.

    Task is `periodic` by default. It means that after task execution finished
    it will be started again after sleeping for `sleep_interval` seconds.

    Multiple instances of the service task can be started in parallel.
    It is started in single instance by default but you can control this behavior
    using `workers` argument.
    """
    if workers < 1:
        raise ValueError("Number of service task workers should be gte 1")
    if sleep_interval < 0:
        raise ValueError("Sleeping interval should be gte 0")

    def wrapper(f):
        f.service_task = True
        f.service_task_definition = {
            'periodic': periodic,
            'sleep_interval': sleep_interval,
            'workers': workers,
        }
        return f

    return wrapper
