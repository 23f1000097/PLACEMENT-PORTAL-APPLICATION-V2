from flask import Blueprint, g, jsonify, request

from extensions import db
from models.application import Application
from models.job import JobPosition
from models.placement import Placement
from utils.decorators import role_required
from utils.validators import parse_date, require_fields

placement_bp = Blueprint("placement", __name__)


def scoped_placement_query():
    user = g.current_user
    query = Placement.query
    if user.role == "student":
        if not user.student:
            return query.filter(False)
        return query.filter_by(student_id=user.student.id)
    if user.role == "company":
        if not user.company:
            return query.filter(False)
        return query.filter_by(company_id=user.company.id)
    return query


@placement_bp.route("/", methods=["GET"])
@role_required({"admin", "company", "student"})
def list_placements():
    placements = scoped_placement_query().order_by(Placement.placed_at.desc()).all()
    return jsonify({
        "placements": [placement.to_dict() for placement in placements]
    }), 200


@placement_bp.route("/", methods=["POST"])
@role_required({"admin", "company"})
def create_placement():
    payload = request.get_json(silent=True) or {}
    missing = require_fields(payload, ["student_id", "company_name", "job_title"])
    if missing:
        return jsonify({"message": f"Missing fields: {', '.join(missing)}"}), 400

    if g.current_user.role == "company":
        company = g.current_user.company
        if not company or not company.approved:
            return jsonify({"message": "Company is awaiting admin approval"}), 403
        payload["company_id"] = company.id
        payload["company_name"] = company.company_name

    placement = Placement(
        student_id=payload["student_id"],
        company_id=payload.get("company_id"),
        job_id=payload.get("job_id"),
        application_id=payload.get("application_id"),
        company_name=payload["company_name"],
        job_title=payload["job_title"],
        package=payload.get("package"),
        joining_date=parse_date(payload.get("joining_date")),
    )
    db.session.add(placement)

    if placement.application_id:
        application = Application.query.get(placement.application_id)
        if application:
            application.status = "Placed"

    db.session.commit()
    return jsonify({
        "message": "Placement recorded",
        "placement": placement.to_dict()
    }), 201


@placement_bp.route("/from-application/<int:application_id>", methods=["POST"])
@role_required({"admin", "company"})
def create_from_application(application_id):
    application = Application.query.get_or_404(application_id)

    if g.current_user.role == "company":
        company = g.current_user.company
        if not company or application.job.company_id != company.id:
            return jsonify({"message": "Unauthorized"}), 403

    payload = request.get_json(silent=True) or {}
    company = application.job.company if application.job else None
    placement = Placement(
        student_id=application.student_id,
        company_id=company.id if company else None,
        job_id=application.job_id,
        application_id=application.id,
        company_name=company.company_name if company else payload.get("company_name"),
        job_title=application.job.title if application.job else payload.get("job_title"),
        package=payload.get("package") or (application.job.salary if application.job else None),
        joining_date=parse_date(payload.get("joining_date")),
    )
    application.status = "Placed"
    db.session.add(placement)
    db.session.commit()

    return jsonify({
        "message": "Placement recorded from application",
        "placement": placement.to_dict()
    }), 201
