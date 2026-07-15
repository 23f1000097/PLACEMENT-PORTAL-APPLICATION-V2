from flask import Blueprint, g, jsonify, request

from extensions import db
from models.application import Application
from models.job import JobPosition
from models.placement import Placement
from utils.decorators import role_required
from utils.validators import parse_datetime

application_bp = Blueprint("application", __name__)


def scoped_application_query():
    user = g.current_user
    query = Application.query

    if user.role == "student":
        if not user.student:
            return query.filter(False)
        return query.filter_by(student_id=user.student.id)

    if user.role == "company":
        if not user.company:
            return query.filter(False)
        return query.join(JobPosition).filter(JobPosition.company_id == user.company.id)

    return query


@application_bp.route("/", methods=["GET"])
@role_required({"admin", "company", "student"})
def list_applications():
    status = request.args.get("status", "").strip()
    query = scoped_application_query().order_by(Application.applied_at.desc())
    if status:
        query = query.filter(Application.status == status)
    return jsonify({
        "applications": [application.to_dict() for application in query.all()]
    }), 200


@application_bp.route("/<int:application_id>", methods=["GET"])
@role_required({"admin", "company", "student"})
def application_detail(application_id):
    application = scoped_application_query().filter(Application.id == application_id).first_or_404()
    return jsonify({"application": application.to_dict()}), 200


@application_bp.route("/<int:application_id>/status", methods=["PATCH"])
@role_required({"admin", "company"})
def update_status(application_id):
    application = scoped_application_query().filter(Application.id == application_id).first_or_404()
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    allowed = {"Applied", "Shortlisted", "Interview", "Selected", "Rejected", "Placed"}
    if status not in allowed:
        return jsonify({"message": f"Status must be one of: {', '.join(sorted(allowed))}"}), 400

    application.status = status
    if "feedback" in payload:
        application.feedback = payload.get("feedback")
    if "interview_at" in payload:
        application.interview_at = parse_datetime(payload.get("interview_at"))
    if "offer_letter" in payload:
        application.offer_letter = payload.get("offer_letter")

    company = application.job.company if application.job else None

    if status == "Placed" and not application.placement:
        db.session.add(Placement(
            student_id=application.student_id,
            company_id=company.id if company else None,
            job_id=application.job_id,
            application_id=application.id,
            company_name=company.company_name if company else None,
            job_title=application.job.title if application.job else None,
            package=application.job.salary if application.job else None,
        ))

    db.session.commit()

    if application.student and application.student.user and status in {"Interview", "Shortlisted", "Selected", "Rejected", "Placed"}:
        from tasks import notify_student_status_update
        notify_student_status_update.delay(
            application.student.user.email,
            application.student.user.name,
            application.job.title if application.job else 'the position',
            status,
            company.company_name if company else 'Company',
            application.interview_at.isoformat() if status == "Interview" and application.interview_at else None,
        )

    return jsonify({
        "message": "Application updated",
        "application": application.to_dict()
    }), 200
