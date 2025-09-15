import uuid
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from pydantic import BaseModel
from sqlalchemy import String, ForeignKey

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


