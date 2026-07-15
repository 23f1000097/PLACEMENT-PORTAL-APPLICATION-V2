import os

from app import app
from extensions import db
from models.user import User


with app.app_context():
    admin_email = os.getenv("ADMIN_EMAIL", "admin@placement.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_name = os.getenv("ADMIN_NAME", "Administrator")

    admin = User.query.filter_by(
        email=admin_email
    ).first()

    if not admin:

        admin = User(
            name=admin_name,
            email=admin_email,
            role="admin"
        )

        admin.set_password(admin_password)

        db.session.add(admin)
        db.session.commit()

        print("Admin Created Successfully")

    else:
        print("Admin Already Exists")
