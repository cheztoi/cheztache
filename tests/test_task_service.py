
import pytest
import arrow
from chez.tache.models import db, Task, Project, Tag
from chez.tache.services import TaskService
from chez.tache.services.task import TaskServiceParseException


class TestTaskService(object):

    @pytest.fixture
    def ts(self, app):
        return TaskService()

    def test_create_and_get(self, ts):
        count = Task.query.count()
        task = ts.create(description=u'Hello world')
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

        options = ts.parse_project_option({}, 'project', u'test')
        assert 'project' in options
        assert isinstance(options['project'], Project)
        assert options['project'].id is None
        assert options['project'].name == 'test'

        # Test that the project wasn't commited
        assert Task.query.count() == count

        with pytest.raises(TaskServiceParseException):
            ts.parse_project_option({'project': None}, 'project', u'test')

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
        arguments = u'hello world pri:H pro:test due:today waituntil:yesterday'
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
        assert task.due.to('local').date() == arrow.now().date()
        assert task.waituntil.to(
            'local').date() == arrow.now().replace(days=-1).date()

    def test_parse_date_option(self, ts):
        # test weekday shorthand
        options = ts.parse_date_option({}, 'test', 'Th')
        assert 'test' in options
        assert options['test'].format('dddd').lower() == 'thursday'
        assert options['test'] > arrow.now().floor('day')
        assert options['test'] < arrow.now().replace(weeks=1)

        # test formated date
        date = arrow.get('2015-07-22')
        options = ts.parse_date_option({}, 'test', date.format('YYYY-MM-DD'))
        assert 'test' in options
        assert options['test'].date() == date.date()

        # test shortcuts
        now = arrow.now()
        shortcuts = {
            'today': now,
            'yesterday': now.replace(days=-1),
            'tomorrow': now.replace(days=1),
        }
        for shortcut, day in shortcuts.iteritems():
            options = ts.parse_date_option({}, 'test', shortcut)
            assert options['test'].date() == day.date()

        # test duplicate
        with pytest.raises(TaskServiceParseException):
            ts.parse_date_option(options, 'test', 'Mo')

        # test invalid date
        with pytest.raises(TaskServiceParseException):
            ts.parse_date_option({}, 'val', 'Mayday')

    def test_parse_due_date_option(self, ts):
        options = ts.parse_due_date({}, 'test', 'Mo')
        assert 'due' in options

    def test_waituntil_date_option(self, ts):
        options = ts.parse_waituntil_date({}, 'test', 'Wed')
        assert 'waituntil' in options

    def test_tags(self, ts):
        arguments = u'hello world +test +hello +world'

        count = Task.query.count()
        tag_count = Tag.query.count()

        task = ts.from_arguments(arguments.split(' '))
        assert Task.query.count() == (count + 1)
        assert Tag.query.count() == (tag_count + 3)
        assert task is not None
        assert task.description == 'hello world'
        assert len(task.tags) == 3
        assert sorted(list(task.tags)) == sorted(['test', 'hello', 'world'])

    def test_filter_by_arguments(self, ts):
        arguments = u'hello world +test due:today'
        task = ts.from_arguments(arguments.split(' '))
        assert task is not None
        assert task.id is not None
        assert Task.query.count() > 0

        # positives, should find task
        arg_sets = [
            u'+test',
            u'hello',
            u'hello world',
            u'hello +test',
            u'+test due:today',
            u'+test +today',
            u'+test +TODAY',
        ]
        for arg in arg_sets:
            query = ts.filter_by_arguments(arg.split(' '))
            assert query is not None
            assert query.count() > 0
            assert task in query.all()

        # negatives, should not find task
        arg_sets = [
            u'-test',
            u'hn',
            u'hello norld',
            u'hello -test',
            u'due:tomorrow +test',
            u'+tomorrow +test',
            u'due:yesterday +test',
            u'+test +YESTERDAY',
        ]
        for arg in arg_sets:
            query = ts.filter_by_arguments(arg.split(' '))
            assert query is not None
            assert task not in query.all()

    def test_virtual_tags(self, ts):
        arguments = u'hello world +test due:yesterday'
        task = ts.from_arguments(arguments.split(' '))
        assert task is not None
        assert task.id is not None
        assert task.due < arrow.now()
        assert Task.query.count() > 0

        arg_sets = [
            u'+overdue',
            u'+test +overdue',
            u'+yesterday',
            u'+test due:yesterday',
        ]
        for arg in arg_sets:
            query = ts.filter_by_arguments(arg.split(' '))
            assert query is not None
            assert query.count() > 0
            assert task in query.all()

        task.due = arrow.now().replace(days=1)
        db.session.add(task)
        db.session.commit()

        arg_sets = [
            u'+tomorrow',
            u'+test +tomorrow',
        ]
        for arg in arg_sets:
            query = ts.filter_by_arguments(arg.split(' '))
            assert query is not None
            assert query.count() > 0
            assert task in query.all()
