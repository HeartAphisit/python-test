import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.main import app
from src.database import get_session
from src.models import User, UserRole, Booking, BookingStatus
from src.auth import hash_password


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="users")
def users_fixture(session: Session):
    """Create admin and regular users for testing"""
    admin_user = User(
        username="admin",
        email="admin@test.com",
        full_name="Admin User",
        role=UserRole.admin,
        is_active=True,
        hashed_password=hash_password("admin123")
    )

    regular_user = User(
        username="user",
        email="user@test.com",
        full_name="Regular User",
        role=UserRole.user,
        is_active=True,
        hashed_password=hash_password("user123")
    )

    session.add(admin_user)
    session.add(regular_user)
    session.commit()
    session.refresh(admin_user)
    session.refresh(regular_user)

    return {"admin": admin_user, "user": regular_user}


# Test login functionality with different user credentials
def test_login_with_different_credentials(client: TestClient, users):
    """Test login with admin and regular user credentials"""

    # Test admin login
    admin_response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert admin_response.status_code == 200
    assert "access_token" in admin_response.json()

    # Test regular user login
    user_response = client.post(
        "/auth/login",
        json={"username": "user", "password": "user123"}
    )
    assert user_response.status_code == 200
    assert "access_token" in user_response.json()

    # Test invalid credentials
    invalid_response = client.post(
        "/auth/login",
        json={"username": "user", "password": "wrongpassword"}
    )
    assert invalid_response.status_code == 401


# Test booking functionality for both admin and non-admin users
def test_booking_functionality_for_different_users(client: TestClient, users, session: Session):
    """Test that both admin and regular users can create bookings"""

    # Get tokens for both users
    admin_token = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"}
    ).json()["access_token"]

    user_token = client.post(
        "/auth/login",
        json={"username": "user", "password": "user123"}
    ).json()["access_token"]

    # Admin creates a booking
    admin_booking = client.post(
        "/bookings/",
        json={"booking_date": "9am-10am", "status": "confirmed"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_booking.status_code == 201
    assert admin_booking.json()["booking_date"] == "9am-10am"

    # Regular user creates a booking
    user_booking = client.post(
        "/bookings/",
        json={"booking_date": "2pm-3pm", "status": "pending"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert user_booking.status_code == 201
    assert user_booking.json()["booking_date"] == "2pm-3pm"


# Test that admin can view all bookings while regular users can only see their own
def test_admin_vs_user_booking_access(client: TestClient, users, session: Session):
    """Test role-based access to bookings"""

    # Get tokens
    admin_token = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"}
    ).json()["access_token"]

    user_token = client.post(
        "/auth/login",
        json={"username": "user", "password": "user123"}
    ).json()["access_token"]

    # Create bookings for both users directly in database
    admin_booking = Booking(
        user_id=users["admin"].id,
        booking_date="admin-slot",
        status=BookingStatus.confirmed
    )
    user_booking = Booking(
        user_id=users["user"].id,
        booking_date="user-slot",
        status=BookingStatus.pending
    )
    session.add(admin_booking)
    session.add(user_booking)
    session.commit()

    # Admin should see ALL bookings (both admin and user bookings)
    admin_view = client.get(
        "/bookings/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_view.status_code == 200
    admin_bookings = admin_view.json()
    assert len(admin_bookings) == 2  # Should see both bookings

    # Regular user should see ONLY their own booking
    user_view = client.get(
        "/bookings/",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert user_view.status_code == 200
    user_bookings = user_view.json()
    assert len(user_bookings) == 1  # Should see only their booking
    assert user_bookings[0]["user_id"] == users["user"].id
    assert user_bookings[0]["booking_date"] == "user-slot"


# Test that regular users cannot access admin-only endpoints
def test_admin_only_endpoints_access(client: TestClient, users):
    """Test that regular users cannot access admin-only endpoints"""

    user_token = client.post(
        "/auth/login",
        json={"username": "user", "password": "user123"}
    ).json()["access_token"]

    admin_token = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"}
    ).json()["access_token"]

    # Regular user should NOT access detailed bookings endpoint
    user_response = client.get(
        "/bookings/all",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert user_response.status_code == 403

    # Admin should be able to access detailed bookings endpoint
    admin_response = client.get(
        "/bookings/all",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_response.status_code == 200
