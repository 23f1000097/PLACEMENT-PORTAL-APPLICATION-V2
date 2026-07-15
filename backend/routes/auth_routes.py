from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required

from extensions import db
from models.company import Company
from models.student import Student
from models.user import User
from routes.services.cache_service import (
    ADMIN_COMPANIES_PREFIX,
    ADMIN_STUDENTS_PREFIX,
    clear_cache,
)
from utils.decorators import current_user
from utils.validators import (
    require_fields,
    validate_email,
    validate_password,
    validate_positive_number,
    validate_year,
)

auth_bp = Blueprint("auth", __name__)


def auth_response(user):
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )
    return {
        "access_token": token,
        "user": user.to_dict()
    }


@auth_bp.route("/register/student", methods=["POST"])
def register_student():
    payload = request.get_json(silent=True) or {}
    missing = require_fields(payload, ["name", "email", "password"])
    if missing:
        return jsonify({"message": f"Missing fields: {', '.join(missing)}"}), 400

    if not validate_email(payload["email"]):
        return jsonify({"message": "Invalid email"}), 400
    if not validate_password(payload["password"]):
        return jsonify({"message": "Password must be at least 6 characters"}), 400
    if User.query.filter_by(email=payload["email"].lower()).first():
        return jsonify({"message": "Email already registered"}), 409

    cgpa = None
    if payload.get("cgpa") not in (None, ""):
        cgpa, err = validate_positive_number(payload["cgpa"], field_name="CGPA")
        if err or cgpa > 10:
            return jsonify({"message": err or "CGPA must be between 0 and 10"}), 400

    passing_year = None
    if payload.get("passing_year") not in (None, ""):
        passing_year, err = validate_year(payload["passing_year"], field_name="Passing year")
        if err:
            return jsonify({"message": err}), 400

    user = User(
        name=payload["name"].strip(),
        email=payload["email"].lower().strip(),
        role="student"
    )
    user.set_password(payload["password"])
    student = Student(
        user=user,
        college=payload.get("college"),
        phone=payload.get("phone"),
        degree=payload.get("degree"),
        branch=payload.get("branch"),
        specialization=payload.get("specialization"),
        cgpa=cgpa,
        passing_year=passing_year,
        skills=payload.get("skills"),
    )
    db.session.add(student)
    db.session.commit()
    clear_cache(ADMIN_STUDENTS_PREFIX)
    return jsonify(auth_response(user)), 201


@auth_bp.route("/register/company", methods=["POST"])
def register_company():
    payload = request.get_json(silent=True) or {}
    missing = require_fields(payload, ["name", "email", "password", "company_name"])
    if missing:
        return jsonify({"message": f"Missing fields: {', '.join(missing)}"}), 400

    if not validate_email(payload["email"]):
        return jsonify({"message": "Invalid email"}), 400
    if not validate_password(payload["password"]):
        return jsonify({"message": "Password must be at least 6 characters"}), 400
    if User.query.filter_by(email=payload["email"].lower()).first():
        return jsonify({"message": "Email already registered"}), 409

    user = User(
        name=payload["name"].strip(),
        email=payload["email"].lower().strip(),
        role="company"
    )
    user.set_password(payload["password"])
    company = Company(
        user=user,
        company_name=payload["company_name"].strip(),
        industry=payload.get("industry"),
        hr_contact=payload.get("hr_contact"),
        contact_email=payload.get("contact_email"),
        phone=payload.get("phone"),
        website=payload.get("website"),
        location=payload.get("location"),
        description=payload.get("description"),
    )
    db.session.add(company)
    db.session.commit()
    clear_cache(ADMIN_COMPANIES_PREFIX)
    return jsonify({
        **auth_response(user),
        "message": "Company registered. Awaiting admin approval."
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    missing = require_fields(payload, ["email", "password"])
    if missing:
        return jsonify({"message": f"Missing fields: {', '.join(missing)}"}), 400

    user = User.query.filter_by(email=payload["email"].lower().strip()).first()
    if not user or not user.check_password(payload["password"]):
        return jsonify({"message": "Invalid email or password"}), 401
    if not user.is_active:
        return jsonify({"message": "Account is deactivated"}), 403

    return jsonify(auth_response(user)), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = current_user()
    if not user:
        return jsonify({"message": "User not found"}), 404

    profile = None
    if user.role == "student" and user.student:
        profile = user.student.to_dict()
    if user.role == "company" and user.company:
        profile = user.company.to_dict()

    return jsonify({
        "user": user.to_dict(),
        "profile": profile
    }), 200
