
from chez.tache.models import db, Project
from .base import BaseService


class ProjectService(BaseService):
    """Project Service manager"""

    def get(self, name):
        """Get a project by name"""
        return Project.query.filter_by(name=name.strip().lower()).first()

    def create(self, name):
        """Create a project by name"""
        project = Project(name=name.strip().lower())
        db.session.add(project)
        db.session.commit()
        return project

    def get_or_create(self, name):
        project = self.get(name=name)
        if not project:
            project = self.create(name=name)
        return project
