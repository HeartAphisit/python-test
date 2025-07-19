from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class BookingStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


class UserBase(SQLModel):
    username: str = Field(
        index=True,
        unique=True,
        min_length=3,
        max_length=50
    )
    email: str = Field(
        index=True,
        unique=True
    )
    full_name: Optional[str] = Field(
        default=None,
        max_length=100
    )
    role: UserRole = Field(default=UserRole.user)
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)


class UserCreate(UserBase):
    password: str = Field(min_length=8)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "johndoe",
                    "email": "johndoe@example.com",
                    "full_name": "John Doe",
                    "password": "secretpassword123",
                    "role": "user",
                    "is_active": True
                }
            ]
        }
    }


class UserUpdate(UserBase):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserReadWithPassword(UserRead):
    hashed_password: str


# Authentication Models
class Token(SQLModel):
    access_token: str
    token_type: str


class TokenData(SQLModel):
    username: Optional[str] = None


class UserLogin(SQLModel):
    username: str
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "johndoe",
                    "password": "secretpassword123"
                }
            ]
        }
    }


class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    booking_date: str = Field(min_length=1, max_length=50)
    status: BookingStatus = Field(default=BookingStatus.pending)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": 1,
                    "booking_date": "10am-11am",
                    "status": "pending"
                }
            ]
        }
    }


class BookingBase(SQLModel):
    booking_date: str = Field(min_length=1, max_length=50)
    status: BookingStatus = Field(default=BookingStatus.pending)


class BookingCreate(BookingBase):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "booking_date": "10am-11am",
                    "status": "pending"
                }
            ]
        }
    }


class BookingUpdate(SQLModel):
    booking_date: Optional[str] = Field(
        default=None, min_length=1, max_length=50)
    status: Optional[BookingStatus] = None


class BookingRead(BookingBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class BookingReadWithUser(BookingRead):
    user: UserRead
