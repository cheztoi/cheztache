
from .base import db, Base


class Tag(Base):
    """Tag model"""
    name = db.Column(db.Unicode, nullable=False, unique=True)
