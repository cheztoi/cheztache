
from sqlalchemy import sql
from sqlalchemy.ext.associationproxy import association_proxy
from .base import db, Base
from .project import Project
from .tag import Tag


def default_task_number(context):
    return context.connection.execute(
        sql.select([sql.func.ifnull(sql.func.max(Task.number), 0) + 1])
    ).scalar()


tasks_tags = db.Table(
    'tasks_tags',
    db.Column('task_id', db.UUID(binary=False), db.ForeignKey('task.id'),
              primary_key=True),
    db.Column('tag_id', db.UUID(binary=False), db.ForeignKey('tag.id'),
              primary_key=True))


class Task(Base):
    PRIORITY_VALUES = (
        (u'l', u'Low'),
        (u'm', u'Medium'),
        (u'h', u'High'),
    )

    project_id = db.Column(db.UUID(binary=False), db.ForeignKey(Project.id))
    project = db.relationship(Project,
                              backref=db.backref("tasks", lazy='dynamic'))

    description = db.Column(db.UnicodeText, nullable=False)
    priority = db.Column(db.Choice(PRIORITY_VALUES))
    due = db.Column(db.Arrow)
    waituntil = db.Column(db.Arrow)
    completed = db.Column(db.Arrow)

    number = db.Column(db.Integer, unique=True, default=default_task_number)

    tags_rel = db.relationship(Tag, secondary=tasks_tags,
                               backref=db.backref('tasks', lazy='dynamic'))
    tags = association_proxy('tags_rel', 'name',
                             creator=lambda name: Tag(name=name))
