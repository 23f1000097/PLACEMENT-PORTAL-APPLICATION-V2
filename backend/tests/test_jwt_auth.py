"""JWT auth flow tests — verifies the exact frontend<->backend token handshake.

Mirrors what the Vue frontend does:
  1. POST /api/auth/login            -> get access_token (like AuthPage login)
  2. GET protected endpoints with    Authorization: Bearer <token>
  3. role_required() outcomes: valid / missing / malformed / expired / wrong-role
"""
import datetime

from tests.conftest import auth_header, make_token


LOGIN = "/api/auth/login"
DASHBOARD = "/api/student/dashboard"
PROFILE = "/api/student/profile"


# ---------------------------------------------------------------- login flow

class TestLogin:
    def test_login_returns_token_and_user(self, client, student_user):
        res = client.post(LOGIN, json={"email": "anjali@test.com", "password": "secret123"})
        assert res.status_code == 200
        body = res.get_json()
        assert "access_token" in body and body["access_token"]
        assert body["user"]["role"] == "student"
        assert body["user"]["email"] == "anjali@test.com"

    def test_login_wrong_password_401(self, client, student_user):
        res = client.post(LOGIN, json={"email": "anjali@test.com", "password": "wrong"})
        assert res.status_code == 401

    def test_login_token_actually_works_on_protected_route(self, client, student_user):
        """End-to-end: token from login must be accepted by a protected endpoint."""
        token = client.post(
            LOGIN, json={"email": "anjali@test.com", "password": "secret123"}
        ).get_json()["access_token"]
        res = client.get(DASHBOARD, headers=auth_header(token))
        assert res.status_code == 200, res.get_json()


# -------------------------------------------------------- token verification

class TestTokenValidation:
    def test_missing_token_is_401(self, client, student_user):
        res = client.get(DASHBOARD)
        assert res.status_code == 401

    def test_garbage_token_is_4xx(self, client, student_user):
        res = client.get(DASHBOARD, headers=auth_header("not.a.jwt"))
        assert res.status_code in (401, 422)

    def test_expired_token_is_401(self, app, client, student_user):
        token = make_token(app, student_user, "student",
                           expires_delta=datetime.timedelta(seconds=-1))
        res = client.get(DASHBOARD, headers=auth_header(token))
        assert res.status_code == 401

    def test_wrong_scheme_rejected(self, app, client, student_user):
        token = make_token(app, student_user, "student")
        res = client.get(DASHBOARD, headers={"Authorization": f"Token {token}"})
        assert res.status_code in (401, 422)

    def test_token_of_deleted_user_is_404(self, app, client):
        token = make_token(app, 9999, "student")
        res = client.get(DASHBOARD, headers=auth_header(token))
        assert res.status_code == 404


# ------------------------------------------------------------ role guarding

class TestRoleGuard:
    def test_admin_token_on_student_route_is_403(self, app, client, student_user):
        res = client.post(LOGIN, json={"email": "admin@placement.com", "password": "admin123"})
        admin_token = res.get_json()["access_token"]
        res = client.get(DASHBOARD, headers=auth_header(admin_token))
        assert res.status_code == 403

    def test_student_token_on_admin_route_is_403(self, app, client, student_user):
        token = make_token(app, student_user, "student")
        res = client.get("/api/admin/students", headers=auth_header(token))
        assert res.status_code == 403

    def test_deactivated_user_is_403(self, app, client, student_user):
        from extensions import db
        from models.user import User
        with app.app_context():
            user = db.session.get(User, student_user)
            user.is_active = False
            db.session.commit()
        token = make_token(app, student_user, "student")
        res = client.get(DASHBOARD, headers=auth_header(token))
        assert res.status_code == 403


# ---------------------------------------------- the actual reported symptom

class TestStudentDrivesFlow:
    """Full reproduction of the bug report: student logs in, drives must appear."""

    def test_dashboard_returns_approved_drives(self, app, client, student_user, approved_drive):
        token = client.post(
            LOGIN, json={"email": "anjali@test.com", "password": "secret123"}
        ).get_json()["access_token"]

        res = client.get(DASHBOARD, headers=auth_header(token))
        assert res.status_code == 200
        drives = res.get_json()["approved_drives"]
        titles = [d["title"] for d in drives]
        assert "ece" in titles, f"approved drive missing, got {titles}"
        assert "pending-job" not in titles, "pending drive must NOT be shown"

    def test_dashboard_and_profile_same_token(self, app, client, student_user, approved_drive):
        """loadStudent() fires both requests with one token - both must pass."""
        token = client.post(
            LOGIN, json={"email": "anjali@test.com", "password": "secret123"}
        ).get_json()["access_token"]
        r1 = client.get(DASHBOARD, headers=auth_header(token))
        r2 = client.get(PROFILE, headers=auth_header(token))
        assert r1.status_code == 200 and r2.status_code == 200
        assert len(r1.get_json()["approved_drives"]) == 1
        assert r2.get_json()["student"]["branch"] == "ece"

    def test_cache_bust_param_does_not_break_endpoint(self, app, client, student_user, approved_drive):
        """Frontend appends ?_t=<ms> to every GET - backend must ignore it."""
        token = make_token(app, student_user, "student")
        res = client.get(DASHBOARD + "?_t=1784084046723", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.get_json()["approved_drives"]) == 1

    def test_api_responses_not_cacheable(self, app, client, student_user):
        """no-store headers must be present so browsers never serve stale data."""
        token = make_token(app, student_user, "student")
        res = client.get(DASHBOARD, headers=auth_header(token))
        assert "no-store" in res.headers.get("Cache-Control", ""), (
            "API responses must send Cache-Control: no-store"
        )
