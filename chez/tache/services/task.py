
import re
import arrow
from sqlalchemy import and_, not_
from sqlalchemy_utils import escape_like
from .base import BaseService, BaseServiceException
from .project import ProjectService
from chez.tache.models import db, Task, Project, Tag


class TaskService(BaseService):
    """Service to manage tasks"""

    DEFAULT_OPTION_REGEX = re.compile(r'^(\w+):(.*?)$')
    DEFAULT_TAG_REGEX = re.compile(r'^([\+-])(\w+)$')

    def __init__(self, option_regex=DEFAULT_OPTION_REGEX,
                 tag_regex=DEFAULT_TAG_REGEX):
        self.option_regex = option_regex
        self.tag_regex = tag_regex

    def create(self, **kwargs):
        """Create a task with `**kwargs`"""
        task = Task(**kwargs)
        db.session.add(task)
        db.session.commit()
        return task

    def parse_date(self, value):
        """
        Parses a date and returns the value as an arrow type

        :returns: arrow object
        :raises TaskServiceParseException: on parse error
        """
        value = value.strip()

        # try to parse formated date
        try:
            return arrow.get(value)
        except arrow.parser.ParserError:
            pass

        shortcuts = {
            'today': arrow.now(),
            'yesterday': arrow.now().replace(days=-1),
            'tomorrow': arrow.now().replace(days=1),
        }
        shortcut_value = value.lower()
        if shortcut_value in shortcuts:
            return shortcuts[shortcut_value]

        weekday = value.lower()
        now = arrow.now()
        next_week = now.replace(days=8)
        while now <= next_week:
            if now.format('dddd').lower().startswith(weekday):
                return now
            now = now.replace(days=1)

        raise TaskServiceParseException(
            "Invalid date format: {}".format(value))

    def parse_project_option(self, options, name, value):
        """
        Parses a project by getting or creating it

        :param options: options to modify and return
        :param value: project name
        :raises TaskServiceParseException: if the project was already set in
            options
        """
        if 'project' in options:
            raise TaskServiceParseException("More than one project defined")

        if not value:
            options['project'] = None
            return options

        ps = ProjectService()
        options['project'] = ps.get_or_create(value, commit=False)
        return options

    def parse_priority_option(self, options, name, value):
        """Parses the priority option"""
        if 'priority' in options:
            raise TaskServiceParseException("More than one priority defined")

        if not value:
            options['priority'] = None
            return options

        priority = value[0].lower()
        if priority not in [x[0] for x in Task.PRIORITY_VALUES]:
            raise TaskServiceParseException(
                "Invalid priority value: {}".format(priority))

        options['priority'] = priority
        return options

    def parse_date_option(self, options, name, value):
        """Helper to parse date option"""
        if name in options:
            raise TaskServiceParseException(
                "More than one {} date defined".format(name))
        try:
            options[name] = self.parse_date(value)
            return options
        except TaskServiceParseException:
            raise TaskServiceParseException(
                "Invalid {0} date: {1}".format(name, value))

    def parse_due_date(self, options, name, value):
        """Parses due date"""
        return self.parse_date_option(options, 'due', value)

    def parse_waituntil_date(self, options, name, value):
        """Parses waituntil date"""
        return self.parse_date_option(options, 'waituntil', value)

    def parse_option(self, options, name, value):
        """
        Parses options and sets the proper options in the dictionary used for
        creating tasks

        :raises TaskServiceParseException: if key is too ambiguous
        """
        option_types = {
            'project': self.parse_project_option,
            'priority': self.parse_priority_option,
            'due': self.parse_due_date,
            'waituntil': self.parse_waituntil_date,
        }
        option_func = None
        for k, v in option_types.items():
            if k.startswith(name):
                if option_func:
                    msg = "Key: {} is too ambiguous".format(name)
                    raise TaskServiceParseException(msg)
                option_func = v
        return option_func(options, name, value)

    def create_date_filter(self, column, day):
        """Creates date filters which matches ranges"""
        start, end = day.span('day')
        return and_(column >= start, column <= end)

    @property
    def virtual_tags(self):
        """Creates the filters for virtual tags"""
        now = arrow.now()
        return {
            'TODAY': self.create_date_filter(Task.due, now),
            'YESTERDAY': self.create_date_filter(
                Task.due, now.replace(days=-1)),
            'TOMORROW': self.create_date_filter(Task.due, now.replace(days=1)),
            'OVERDUE': and_(Task.due <= now, Task.completed == None),  # noqa
        }

    def parse_arguments(self, arguments, with_filters=False):
        """Parse command line arguemnts and return an options dictionary"""
        description = []
        tags = []
        options = {}
        filters = {'all': []}
        for arg in arguments:
            option_match = self.option_regex.match(arg)
            tag_match = self.tag_regex.match(arg)
            if option_match:
                options = self.parse_option(
                    options, option_match.group(1), option_match.group(2))
            elif tag_match:
                sign = tag_match.group(1)
                tag = tag_match.group(2).lower()
                virtual_tags = self.virtual_tags

                if tag.upper() in virtual_tags:
                    if sign == '-':
                        filters['all'].append(not_(virtual_tags[tag.upper()]))
                    else:
                        filters['all'].append(virtual_tags[tag.upper()])
                elif sign == '+':
                    tags.append(tag)
                else:
                    ilike = u'%{}%'.format(escape_like(tag))
                    filters['all'].append(
                        Task.tags.any(Tag.name.notilike(ilike)))
            else:
                description.append(arg)

        if description:
            options['description'] = ' '.join(description)
        if tags:
            options['tags'] = tags
        if with_filters:
            options['filters'] = filters
        return options

    def from_arguments(self, arguments):
        """Parse command line arguments and create a task, project, etc"""
        options = self.parse_arguments(arguments, with_filters=False)
        if not options.get('description', None):
            raise TaskServiceParseException("Invalid task description")

        return self.create(**options)

    def filter_by_arguments(self, arguments):
        """Parse command line arguments and create a sql query"""
        options = self.parse_arguments(arguments, with_filters=True)
        filters = options.pop('filters', {})

        query = Task.query
        for name, value in options.iteritems():
            column = getattr(Task, name, None)
            if not column:
                raise TaskServiceParseException(
                    "Invalid query param: {}".format(name))

            if isinstance(value, basestring):  # noqa
                query = query.filter(
                    column.ilike(u'%{}%'.format(escape_like(value.strip()))))
            elif isinstance(value, list) and name.lower() == 'tags':
                for val in value:
                    if name.lower() == 'tags':
                        val = u'%{}%'.format(val)
                        query = query.filter(column.any(Tag.name.ilike(val)))
            elif isinstance(value, arrow.Arrow):
                query = query.filter(self.create_date_filter(column, value))
            elif isinstance(value, Project):
                query = query.filter(column == value)
            elif value is None:
                query = query.filter(column == None)  # noqa
            else:
                raise TaskServiceParseException(
                    "Invalid query value: {}".format(value))

        # handle negatives
        for filter in filters['all']:
            query = query.filter(filter)

        return query


class TaskServiceException(BaseServiceException):
    pass


class TaskServiceParseException(TaskServiceException):
    pass
