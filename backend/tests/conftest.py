"""Pytest fixtures for JWT / auth integration tests.

Uses a temporary SQLite DB and SimpleCache so no Redis or real DB is touched.
Config is patched BEFORE importing app, because app.py builds the app at import.
"""
import os
import sys
import tempfile

import pytest

# Make backend modules importable when running pytest from backend/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config as config_module  # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="ppa_test_")
config_module.Config.SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(_tmpdir, "test.db")
config_module.Config.CACHE_TYPE = "SimpleCache"
config_module.Config.CACHE_REDIS_URL = None
config_module.Config.TESTING = True

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models.company import Company  # noqa: E402
from models.job import JobPosition  # noqa: E402
from models.student import Student  # noqa: E402
from models.user import User  # noqa: E402


@pytest.fixture(scope="session")
def app():
    application = create_app()
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Fresh tables for every test (admin user re-seeded)."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        admin = User(name="Administrator", email="admin@placement.com", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
    yield


@pytest.fixture()
def student_user(app):
    """A registered, active student (anjali-like)."""
    with app.app_context():
        user = User(name="anjali", email="anjali@test.com", role="student")
        user.set_password("secret123")
        student = Student(user=user, college="IITM", branch="ece", cgpa=7.0, passing_year=2026)
        db.session.add(student)
        db.session.commit()
        return user.id


@pytest.fixture()
def approved_drive(app):
    """An approved company with one approved+one pending drive."""
    with app.app_context():
        cuser = User(name="mithun", email="company@test.com", role="company")
        cuser.set_password("secret123")
        company = Company(user=cuser, company_name="unt", approved=True)
        db.session.add(company)
        db.session.flush()
        approved = JobPosition(
            company_id=company.id, title="ece", description="nil",
            approved=True, status="Approved", eligibility_branch="ece", minimum_cgpa=7.0,
        )
        pending = JobPosition(
            company_id=company.id, title="pending-job", description="nil",
            approved=False, status="Pending",
        )
        db.session.add_all([approved, pending])
        db.session.commit()
        return approved.id


def make_token(app, user_id, role, expires_delta=None):
    """Mint a token exactly like auth_response() does (identity=str(id))."""
    from flask_jwt_extended import create_access_token
    with app.app_context():
        kwargs = {"identity": str(user_id), "additional_claims": {"role": role}}
        if expires_delta is not None:
            kwargs["expires_delta"] = expires_delta
        return create_access_token(**kwargs)


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}
