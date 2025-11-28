"""Base Schema Module - SQLModel configuration for all apps."""

__all__ = ["Base", "SQLModel"]

import sqlalchemy.orm
import sqlmodel

Base = sqlalchemy.orm.declarative_base()
sqlmodel.SQLModel.metadata = Base.metadata

SQLModel = sqlmodel.SQLModel
