
from chez.tache.models import db, Project
from .base import BaseService


class ProjectService(BaseService):
    """Project Service manager"""

    def get(self, name):
        """Get a project by name"""
        return Project.query.filter_by(name=name.strip().lower()).first()

    def create(self, name, commit=True):
        """
        Create a project by name

        :param commit: commit the created project if True
        """
        project = Project(name=name.strip().lower())
        if commit:
            db.session.add(project)
            db.session.commit()
        return project

    def get_or_create(self, name, commit=True):
        project = self.get(name=name)
        if not project:
            project = self.create(name=name, commit=commit)
        return project
