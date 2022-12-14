"""The :mod:`app.models.user` module contains a ORMs used to persist and retrieve 
data concerning users on HyperSenta
"""
# Author: Christopher Dare


import uuid as uuid_pkg
from datetime import datetime
from typing import Any, Dict, Optional

import phonenumbers
import sqlalchemy as sa
from pydantic import EmailStr, root_validator, validator
from sqlmodel import Column, DateTime, Field, SQLModel

from app.utils.parser import parse_mobile_number
from app.utils.security import make_password

from .abstract import TimeStampedModel


class UserBase(SQLModel):
    first_name: str = Field(description="User's first name", nullable=False)
    last_name: str = Field(description="User's last name", nullable=False)
    full_name: Optional[str] = Field(description="User's last name", nullable=False)
    last_used_organization_name: Optional[str] = Field(description="Name of last used organization", nullable=True)
    last_used_organization_id: Optional[uuid_pkg.UUID] = Field(description="UUID of last used organization", nullable=True)
    mobile: str = Field(
        regex=r"^\+?1?\d{9,15}$",
        index=True,
        nullable=True,
        unique=True,
        description="International country calling format for user's phone number",
    )
    national_mobile_number: Optional[str] = Field(
        nullable=True, description="National calling format for the user's phone number"
    )
    email: EmailStr = Field(
        description="User's email address", index=True, nullable=False, unique=True
    )


class User(UserBase, TimeStampedModel, table=True):
    id: Optional[int] = Field(
        sa_column=Column(
            "id",
            sa.INTEGER(),
            index=True,
            autoincrement=True,
            nullable=False,
            primary_key=True,
        ),
        description="Internal database id for User table. Not to be exposed to client apps or used as foreign key references",
        default=None,
    )
    full_name: Optional[str] = Field(index=True, nullable=False)
    is_active: bool = Field(
        description="Flag to mark user's active status", default=False
    )
    is_superuser: bool = Field(
        description="Flag to mark user's superuser status", default=False
    )
    password: str = Field(description="Hash of user's password")
    last_login: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True)), nullable=True
    )

    @validator("national_mobile_number", pre=True)
    def validate_national_phone_number(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Any:
        mobile_number = values.get("mobile")
        if not mobile_number:
            return v  # so this can be excluded as an unset property in an update
        national_mobile_number = ""
        try:
            national_mobile_number = parse_mobile_number(
                phone_number=mobile_number, international_format=False
            )
        except phonenumbers.NumberParseException:
            pass
        return national_mobile_number

    @validator("full_name", pre=True)
    def validate_full_name(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        return f"{values.get('first_name')} {values.get('last_name')}"

    # meta properties
    __tablename__ = "users"


# Properties to receive via API on creation
class UserCreate(UserBase):
    uuid: uuid_pkg.UUID = uuid_pkg.uuid4()
    email: EmailStr
    password: str = Field(description="Hash of user's password")
    mobile: Optional[str] = ""
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    @validator("password")
    def set_password(cls, v: str, values: Dict[str, Any]) -> Any:
        # ensure that only the hashed password of the user is saved.
        # TODO: Move this behavior to the User object manager
        return make_password(raw_password=v)


class UserRead(UserBase, TimeStampedModel):
    full_name: str = Field(index=True, nullable=False)
    is_active: bool
    last_login: Optional[datetime] = None
    national_mobile_number: str = Field(
        description="National calling format for the user's phone number"
    )


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None
    updated_at: datetime = datetime.now()

    @validator("updated_at", pre=True)
    def validate_updated_at(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        # set user's full name when first and last names are present
        # requirements for full name will differ per use case e.g. create (required) vs update (not required)
        first_name = values.get("first_name")
        last_name = values.get("last_name")
        if first_name and last_name:
            return f"{first_name} {last_name}"
        else:
            return v
