
import re
import arrow
from .base import BaseService, BaseServiceException
from .project import ProjectService
from chez.tache.models import db, Task


class TaskService(BaseService):
    """Service to manage tasks"""

    DEFAULT_OPTION_REGEX = re.compile(r'^(\w+):(.*?)$')
    DEFAULT_TAG_REGEX = re.compile(r'^\+(\w+)$')

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

        value = value.strip()

        # try to parse formated date
        try:
            date = arrow.get(value)
            options[name] = date
            return options
        except arrow.parser.ParserError:
            pass

        weekday = value.lower()
        now = arrow.now()
        next_week = now.replace(days=8)
        while now <= next_week:
            if now.format('dddd').lower().startswith(weekday):
                options[name] = now
                return options
            now = now.replace(days=1)

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

    def from_arguments(self, arguments):
        """Parse command line arguments and create a task, project, etc"""
        description = []
        tags = []
        options = {}
        for arg in arguments:
            option_match = self.option_regex.match(arg)
            tag_match = self.tag_regex.match(arg)
            if option_match:
                options = self.parse_option(
                    options, option_match.group(1), option_match.group(2))
            elif tag_match:
                tags.append(tag_match.group(1).lower())
            else:
                description.append(arg)

        if not description:
            raise TaskServiceException("Invalid task description")

        options['description'] = ' '.join(description)
        options['tags'] = tags
        task = self.create(**options)
        return task


class TaskServiceException(BaseServiceException):
    pass


class TaskServiceParseException(TaskServiceException):
    pass
