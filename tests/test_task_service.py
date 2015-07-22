
import pytest
from chez.tache.models import Task, Project
from chez.tache.services import TaskService
from chez.tache.services.task import TaskServiceParseException


class TestTaskService(object):

    @pytest.fixture
    def ts(self, app):
        return TaskService()

    def test_create_and_get(self, ts):
        count = Task.query.count()
        task = ts.create(description='Hello world')
        assert task is not None
        assert task.id is not None
        assert task.priority is None
        assert task.description == 'Hello world'
        assert Task.query.count() == (count + 1)

        db_task = Task.query.get(task.id)
        assert db_task is not None
        assert db_task.description == task.description

    def test_parse_project_option(self, ts):
        count = Task.query.count()

        options = ts.parse_project_option({}, 'project', 'test')
        assert 'project' in options
        assert isinstance(options['project'], Project)
        assert options['project'].id is None
        assert options['project'].name == 'test'

        # Test that the project wasn't commited
        assert Task.query.count() == count

        with pytest.raises(TaskServiceParseException):
            ts.parse_project_option({'project': None}, 'project', 'test')

    def test_parse_priority_option(self, ts):
        for v in ('high', 'medium', 'low', 'l', 'h', 'm', 'hi', 'lo', None):
            options = ts.parse_priority_option({}, 'priority', v)
            assert 'priority' in options
            if v:
                assert options['priority'] == v.lower()[0]

        with pytest.raises(TaskServiceParseException):
            ts.parse_priority_option({'priority': None}, 'priority', 'high')

        with pytest.raises(TaskServiceParseException):
            ts.parse_priority_option({}, 'priority', 'invalid')

    def test_from_arguments(self, ts):
        arguments = 'hello world pri:H pro:test'
        arguments = arguments.split(' ')

        count = Task.query.count()
        task = ts.from_arguments(arguments)
        assert Task.query.count() == (count + 1)
        assert task is not None
        assert task.id is not None
        assert task.priority.value == 'High'
        assert task.description == 'hello world'
        assert task.project is not None
        assert task.project.id is not None
        assert task.project.name == 'test'
