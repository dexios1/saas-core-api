"""The :mod:`app.models.user` module contains a ORMs used to persist and retrieve 
data concerning users on HyperSenta
"""
# Author: Christopher Dare


from datetime import datetime
from typing import Any, Dict, Optional

import phonenumbers
import sqlalchemy as sa
from pydantic import EmailStr, validator
from sqlmodel import Column, DateTime, Field, SQLModel

from .abstract import TimeStampedModel
from app.utils.parser import parse_mobile_number
from app.utils.security import make_password


class UserBase(SQLModel):
    first_name: str = Field(description="User's first name", nullable=False)
    last_name: str = Field(description="User's last name", nullable=False)
    mobile: str = Field(
        regex=r"^\+?1?\d{9,15}$",
        description="International country calling format for user's phone number",
    )
    email: EmailStr = Field(
        description="User's email address", index=True, nullable=False
    )

    # meta properties
    __tablename__ = "users"


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
        default=None,
    )
    full_name: str = Field(index=True, nullable=False)
    is_active: bool = Field(
        description="Flag to mark user's active status", default=False
    )
    is_superuser: bool = Field(
        description="Flag to mark user's superuser status", default=False
    )
    password: str = Field(description="Hash of user's password")
    national_mobile_number: Optional[str] = Field(
        description="National calling format for the user's phone number"
    )
    last_login: datetime = Field(
        sa_column=Column(DateTime(timezone=True)), nullable=True
    )

    @validator("full_name", pre=True)
    def set_full_name(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        # set user's full name when first and last names are present
        # requirements for full name will differ per use case e.g. create (required) vs update (not required)
        first_name = values.get("first_name")
        last_name = values.get("last_name")
        if first_name and last_name:
            return f"{first_name} {last_name}"
        else:
            return v

    @validator("national_mobile_number", pre=True)
    def set_national_phone_number(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        mobile_number = values.get("mobile")
        if not mobile_number:
            return v # so this can be excluded as an unset property in an update
        national_mobile_number = ""
        try:
            national_mobile_number = parse_mobile_number(phone_number=mobile_number, international_format=False)
        except phonenumbers.NumberParseException:
            pass
        return national_mobile_number


# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(description="Hash of user's password")
    mobile: Optional[str] = ""

    @validator("password", pre=True)
    def set_password(cls, v: str, values: Dict[str, Any]) -> Any:
        # ensure that only the hashed password of the user is saved.
        # TODO: Move this behavior to the User object manager
        return make_password(raw_password=v)


class UserRead(UserBase, TimeStampedModel):
    uuid: str
    full_name: str = Field(index=True, nullable=False)
    is_active: bool
    last_login: datetime
    national_mobile_number: str = Field(
        description="National calling format for the user's phone number"
    )


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None
