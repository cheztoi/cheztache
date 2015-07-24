
import re
import arrow
import copy
from sqlalchemy import and_, not_
from sqlalchemy_utils import escape_like
from .base import BaseService, BaseServiceException
from .project import ProjectService
from chez.tache.models import db, Task, Project, Tag


class Clause(object):
    def __init__(self, name, value=None, isnot=False, clause=None):
        self.name = name
        self.value = value
        self.isnot = isnot
        self.clause = clause

    def get_clause(self):
        """Returns a sqlalchemy for this clause"""
        clause = self.clause

        if clause is None:
            column = getattr(Task, self.name, None)
            if not column:
                raise TaskServiceParseException(
                    "Invalid clause param: {}".format(self.name))

            if self.name.lower() == 'tags':
                if isinstance(self.value, list):
                    _clauses = []
                    for val in self.value:
                        _clauses.append(self.create_tags_clause(val))
                    clause = and_(*_clauses)
                else:
                    clause = self.create_tags_clause(self.value)
            elif isinstance(self.value, basestring):  # noqa
                clause = self.create_text_clause(column, self.value)
            elif isinstance(self.value, arrow.Arrow):
                clause = self.create_date_clause(column, self.value)
            elif isinstance(self.value, Project):
                clause = self.create_project_clause(column, self.value)
            elif self.value is None:
                clause = self.create_null_clause(column)
            else:
                raise TaskServiceParseException(
                    "Invalid query value: {}".format(self.value))

        if self.isnot:
            clause = not_(clause)
        return clause

    def create_null_clause(self, column):
        """Creates a clause for a column which should be null"""
        return column == None  # noqa

    def create_project_clause(self, column, value):
        """Creates a clause for a Project"""
        return column == value

    def create_text_clause(self, column, value):
        """Creates a clause for text"""
        return column.ilike(u'%{}%'.format(escape_like(value.strip())))

    def create_tags_clause(self, tag):
        """Creates a clause for a tag"""
        tag = tag.lower()
        return Task.tags.any(Tag.name.ilike(u'%{}%'.format(escape_like(tag))))

    @classmethod
    def create_date_clause(cls, column, day):
        """Creates date clauses which matches ranges"""
        start, end = day.span('day')
        return and_(column >= start, column <= end)

    @classmethod
    def virtual_tags(cls):
        """Creates the clauses for virtual tags"""
        now = arrow.now()
        return {
            'TODAY': cls.create_date_clause(Task.due, now),
            'YESTERDAY': cls.create_date_clause(
                Task.due, now.replace(days=-1)),
            'TOMORROW': cls.create_date_clause(Task.due, now.replace(days=1)),
            'OVERDUE': and_(Task.due <= now, Task.completed == None),  # noqa
        }


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

    def parse_arguments(self, arguments, with_clauses=False):
        """
        Parse command line arguemnts and return an options dictionary

        :param with_clauses: if True, options will include `'clauses'` which
                             are negative clauses for negative tags and virtual
                             tags. Used internally.
        """
        description = []
        tags = []
        options = {}
        clauses = []
        for arg in arguments:
            option_match = self.option_regex.match(arg)
            tag_match = self.tag_regex.match(arg)
            if option_match:
                options = self.parse_option(
                    options, option_match.group(1), option_match.group(2))
            elif tag_match:
                sign = tag_match.group(1)
                tag = tag_match.group(2).lower()
                virtual_tags = Clause.virtual_tags()

                if tag.upper() in virtual_tags:
                    clauses.append(Clause(name='virtual',
                                          isnot=(sign == '-'),
                                          clause=virtual_tags[tag.upper()]))
                else:
                    if sign == '+':
                        tags.append(tag)
                    elif sign == '-':
                        clause = Clause(name='tags', value=tag, isnot=True)
                        clauses.append(clause)
            else:
                description.append(arg)

        if description:
            options['description'] = ' '.join(description)
        if tags:
            options['tags'] = tags
        if with_clauses:
            options['clauses'] = clauses
        return options

    def from_arguments(self, arguments):
        """Parse command line arguments and create a task, project, etc"""
        options = self.parse_arguments(arguments, with_clauses=False)
        if not options.get('description', None):
            raise TaskServiceParseException("Invalid task description")

        return self.create(**options)

    def filter_by_arguments(self, arguments, defaults=None):
        """
        Parse command line arguments and create a sql query

        :params defaults: default options
        """
        options = self.parse_arguments(arguments, with_clauses=True)
        clauses = options.pop('clauses', [])

        if not defaults:
            defaults = {}
        defaults = copy.deepcopy(defaults)
        clauses.extend(defaults.pop('clauses', []))
        defaults.update(options)

        for name, value in defaults.iteritems():
            clauses.append(Clause(name=name, value=value))

        query = Task.query
        for clause in clauses:
            query = query.filter(clause.get_clause())

        return query


class TaskServiceException(BaseServiceException):
    pass


class TaskServiceParseException(TaskServiceException):
    pass
