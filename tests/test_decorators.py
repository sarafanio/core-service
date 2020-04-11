import pytest

from core_service import task


def test_wrong_task_arguments():
    with pytest.raises(ValueError):
        task(sleep_interval=-1)
    with pytest.raises(ValueError):
        task(workers=0)
