
from .base import db, Base


class Project(Base):
    name = db.Column(db.Unicode(), nullable=False)
