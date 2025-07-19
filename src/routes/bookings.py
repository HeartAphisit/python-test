from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from datetime import datetime, timezone
from ..database import get_session
from ..models import (
    Booking, BookingCreate, BookingRead, BookingUpdate,
    User, UserRole, BookingReadWithUser
)
from ..dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking: BookingCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new booking for the authenticated user"""
    logger.info(f"User {current_user.username} is creating a booking")

    # Create new booking associated with the current user
    db_booking = Booking(
        user_id=current_user.id,
        booking_date=booking.booking_date,
        status=booking.status
    )

    session.add(db_booking)
    session.commit()
    session.refresh(db_booking)

    logger.info(f"Booking {db_booking.id} created successfully")

    return db_booking


@router.get("/", response_model=List[BookingRead])
def read_bookings(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get bookings based on user role:
    - Admin users can see all bookings
    - Regular users can only see their own bookings
    """
    if current_user.role == UserRole.admin:
        logger.info(f"Admin {current_user.username} is fetching all bookings")

        bookings = session.exec(
            select(Booking).offset(skip).limit(limit)
        ).all()
    else:
        logger.info(
            f"User {current_user.username} is fetching only their own bookings")

        bookings = session.exec(
            select(Booking)
            .where(Booking.user_id == current_user.id)
            .offset(skip)
            .limit(limit)
        ).all()

    return bookings


@router.get("/all", response_model=List[BookingReadWithUser])
def read_all_bookings_with_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get all bookings with user information (Admin only)
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can view all bookings with user details"
        )

    logger.info(
        f"Admin {current_user.username} is fetching all bookings with user details")

    # Join query to get bookings with user information
    statement = (
        select(Booking, User)
        .join(User, Booking.user_id == User.id)
        .offset(skip)
        .limit(limit)
    )

    results = session.exec(statement).all()

    # Transform the results into BookingReadWithUser format
    bookings_with_users = []
    for booking, user in results:
        booking_dict = booking.model_dump()
        user_dict = user.model_dump()
        # Remove password hash from user data
        user_dict.pop('hashed_password', None)

        booking_with_user = BookingReadWithUser(
            **booking_dict,
            user=user_dict
        )
        bookings_with_users.append(booking_with_user)

    return bookings_with_users


@router.get("/{booking_id}", response_model=BookingRead)
def read_booking(
    booking_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific booking by ID
    - Admin users can view any booking
    - Regular users can only view their own bookings
    """
    booking = session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Check authorization: admins can view any booking, users can only view their own
    if current_user.role != UserRole.admin and booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own bookings"
        )

    logger.info(
        f"User {current_user.username} is fetching booking ID: {booking_id}")

    return booking


@router.put("/{booking_id}", response_model=BookingRead)
def update_booking(
    booking_id: int,
    booking_update: BookingUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a booking
    - Admin users can update any booking
    - Regular users can only update their own bookings
    """
    booking = session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Check authorization: admins can update any booking, users can only update their own
    if current_user.role != UserRole.admin and booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own bookings"
        )

    logger.info(
        f"User {current_user.username} is updating booking ID: {booking_id}")

    # Update fields if provided
    booking_data = booking_update.model_dump(exclude_unset=True)

    # Update timestamp
    booking_data["updated_at"] = datetime.now(timezone.utc)

    # Apply updates
    for field, value in booking_data.items():
        setattr(booking, field, value)

    session.add(booking)
    session.commit()
    session.refresh(booking)

    logger.info(f"Booking {booking_id} updated successfully")
    print(f"✅ Booking {booking_id} updated successfully")

    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a booking
    - Admin users can delete any booking
    - Regular users can only delete their own bookings
    """
    booking = session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Check authorization: admins can delete any booking, users can only delete their own
    if current_user.role != UserRole.admin and booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own bookings"
        )

    logger.info(
        f"User {current_user.username} is deleting booking ID: {booking_id}")

    session.delete(booking)
    session.commit()

    logger.info(f"Booking {booking_id} deleted successfully")


@router.get("/user/{user_id}", response_model=List[BookingRead])
def read_user_bookings(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get bookings for a specific user (Admin only)
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can view other users' bookings"
        )

    # Check if the user exists
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    logger.info(
        f"Admin {current_user.username} is fetching bookings for user ID: {user_id}")

    bookings = session.exec(
        select(Booking)
        .where(Booking.user_id == user_id)
        .offset(skip)
        .limit(limit)
    ).all()

    return bookings
