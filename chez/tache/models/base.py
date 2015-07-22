
import uuid
from sqlalchemy.ext.declarative import declared_attr
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy_utils import Timestamp
from sqlalchemy_utils import ArrowType, UUIDType, ChoiceType

db = SQLAlchemy()
db.Arrow = ArrowType
db.UUID = UUIDType
db.Choice = ChoiceType


class Base(db.Model, Timestamp):
    """Base model class"""
    __abstract__ = True

    id = db.Column(db.UUID(binary=False), default=uuid.uuid4, primary_key=True)

    @declared_attr
    def __tablename__(cls):
        """ Set __tablename__ to equal the class name to lower """
        return cls.__name__.lower()
