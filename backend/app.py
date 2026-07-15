import os

from flask import Flask, request

from config import Config
from extensions import db, jwt, migrate, cors, cache
from models import (
    Application,
    Company,
    JobPosition,
    Placement,
    Student,
    User,
)

from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.student_routes import student_bp
from routes.company_routes import company_bp
from routes.application_routes import application_bp
from routes.placement_routes import placement_bp


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    os.makedirs(os.path.dirname(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")), exist_ok=True)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": "*"}},
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["Authorization"],
        supports_credentials=True,
    )
    cache.init_app(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(
        os.path.join(app.config["UPLOAD_FOLDER"], "resumes"),
        exist_ok=True
    )
    os.makedirs(
        os.path.join(app.config["UPLOAD_FOLDER"], "company_logos"),
        exist_ok=True
    )
    os.makedirs(
        os.path.join(app.config["UPLOAD_FOLDER"], "offer_letters"),
        exist_ok=True
    )

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(student_bp, url_prefix="/api/student")
    app.register_blueprint(company_bp, url_prefix="/api/company")
    app.register_blueprint(application_bp, url_prefix="/api/application")
    app.register_blueprint(placement_bp, url_prefix="/api/placement")

    @app.after_request
    def add_no_store_headers(response):
        # API responses are per-user and change on every approval/application.
        # Stop the browser from serving a stale cached copy (e.g. an empty
        # drives list captured before a drive was approved).
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    with app.app_context():
        db.create_all()
        ensure_admin_user()

    return app


def ensure_admin_user():
    admin_email = os.getenv("ADMIN_EMAIL", "admin@placement.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_name = os.getenv("ADMIN_NAME", "Administrator")

    admin = User.query.filter_by(email=admin_email).first()
    if admin:
        return

    admin = User(name=admin_name, email=admin_email, role="admin")
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.commit()


app = create_app()
