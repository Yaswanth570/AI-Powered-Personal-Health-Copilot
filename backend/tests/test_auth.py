"""Automated tests for SaaS authentication, user registration, and JWT sessions (Phase 1)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.init_db import (
    DEFAULT_DEMO_USER_EMAIL,
    DEFAULT_DEMO_USER_PASSWORD,
    init_database,
)
from app.db.models import Patient, User
from app.db.session import get_db
from app.main import app

# Isolated in-memory SQLite engine for auth tests
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """Create all tables and seed default records before each test."""
    Base.metadata.create_all(bind=test_engine)
    init_database(engine=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yield a fresh testing database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Yield a FastAPI TestClient with database dependency overridden."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_demo_user_seeded_and_can_login(client: TestClient) -> None:
    """Validate that the initial demo user is seeded and can authenticate immediately."""
    res = client.post(
        "/api/auth/login",
        json={
            "email": DEFAULT_DEMO_USER_EMAIL,
            "password": DEFAULT_DEMO_USER_PASSWORD,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == DEFAULT_DEMO_USER_EMAIL
    assert data["user"]["full_name"] == "Sunita Rao"


def test_register_new_user_success(client: TestClient, db_session: Session) -> None:
    """Validate registering a new user creates an account, JWT token, and primary patient."""
    res = client.post(
        "/api/auth/register",
        json={
            "email": "dr.arun@apollo.example",
            "password": "SecurePassword123!",
            "full_name": "Dr. Arun Varma",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "dr.arun@apollo.example"
    assert data["user"]["full_name"] == "Dr. Arun Varma"

    # Confirm user in DB
    user_id = data["user"]["id"]
    db_user = db_session.get(User, user_id)
    assert db_user is not None
    assert db_user.email == "dr.arun@apollo.example"

    # Confirm primary patient profile was created and linked to this user
    patients = db_session.query(Patient).filter(Patient.user_id == user_id).all()
    assert len(patients) == 1
    assert patients[0].display_name == "Dr. Arun Varma"


def test_register_duplicate_email_conflict(client: TestClient) -> None:
    """Validate that registering an existing email returns HTTP 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "Duplicate User",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_register_validation_errors(client: TestClient) -> None:
    """Validate short passwords or invalid emails are rejected by Pydantic."""
    # Password too short (< 8 chars)
    res_short = client.post(
        "/api/auth/register",
        json={"email": "valid@example.com", "password": "short", "full_name": "John Doe"},
    )
    assert res_short.status_code == 422

    # Invalid email format
    res_bad_email = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "ValidPassword123!", "full_name": "John Doe"},
    )
    assert res_bad_email.status_code == 422


def test_login_invalid_password(client: TestClient) -> None:
    """Validate that login fails with incorrect password."""
    res = client.post(
        "/api/auth/login",
        json={
            "email": DEFAULT_DEMO_USER_EMAIL,
            "password": "WrongPassword2026!",
        },
    )
    assert res.status_code == 401
    assert "invalid email or password" in res.json()["detail"].lower()


def test_login_nonexistent_email(client: TestClient) -> None:
    """Validate that login fails for unknown email."""
    res = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@healthcopilot.local",
            "password": "AnyPassword123!",
        },
    )
    assert res.status_code == 401
    assert "invalid email or password" in res.json()["detail"].lower()


def test_get_me_authenticated(client: TestClient) -> None:
    """Validate that /api/auth/me returns the authenticated user profile."""
    # 1. Login to get token
    login_res = client.post(
        "/api/auth/login",
        json={
            "email": DEFAULT_DEMO_USER_EMAIL,
            "password": DEFAULT_DEMO_USER_PASSWORD,
        },
    )
    token = login_res.json()["access_token"]

    # 2. Call /me with Bearer token
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == DEFAULT_DEMO_USER_EMAIL
    assert user_data["full_name"] == "Sunita Rao"


def test_get_me_unauthenticated_returns_401(client: TestClient) -> None:
    """Validate that accessing /api/auth/me without token returns HTTP 401."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_get_me_invalid_token_returns_401(client: TestClient) -> None:
    """Validate that invalid or tampered JWT returns HTTP 401."""
    res = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert res.status_code == 401


def test_get_me_expired_token_returns_401(client: TestClient) -> None:
    """Validate that an expired token returns HTTP 401."""
    expired_token = create_access_token(
        subject="demo-user-sunita-rao",
        expires_delta=timedelta(seconds=-10),
    )
    res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()
