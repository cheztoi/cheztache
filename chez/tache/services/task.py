
import re
from .base import BaseService, BaseServiceException
from .project import ProjectService
from chez.tache.models import db, Task


class TaskService(BaseService):
    """Service to manage tasks"""

    DEFAULT_OPTION_REGEX = re.compile(r'^(\w+):(.*?)$')

    def __init__(self, option_regex=DEFAULT_OPTION_REGEX):
        self.option_regex = option_regex

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
        options['project'] = ps.get_or_create(value)
        return options

    def parse_option(self, options, name, value):
        """
        Parses options and sets the proper options in the dictionary used for
        creating tasks

        :raises TaskServiceParseException: if key is too ambiguous
        """
        option_types = {
            'project': self.parse_project_option
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
            if option_match:
                options = self.parse_option(options,
                                            option_match.group(1),
                                            option_match.group(2))
            elif arg.startswith('+'):
                tags.append(arg[1:])
            else:
                description.append(arg)

        if not description:
            raise TaskServiceException("Invalid task description")

        options['description'] = ' '.join(description)
        print("options: {}".format(options))
        task = self.create(**options)
        return task


class TaskServiceException(BaseServiceException):
    pass


class TaskServiceParseException(TaskServiceException):
    pass
