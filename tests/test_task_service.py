
import pytest
from chez.tache.models import Task
from chez.tache.services import TaskService


class TestTaskService(object):

    @pytest.fixture
    def ts(self, app):
        return TaskService()

    def test_task_service_create_and_get(self, ts):
        count = Task.query.count()
        task = ts.create(description='Hello world')
        assert task is not None
        assert task.id is not None
        assert Task.query.count() == (count + 1)

        db_task = Task.query.get(task.id)
        assert db_task is not None
        assert db_task.description == task.description
