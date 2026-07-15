from flask import Blueprint, jsonify, request

from extensions import db
from models.application import Application
from models.company import Company
from models.job import JobPosition
from models.placement import Placement
from models.settings import ReminderSettings
from models.student import Student
from models.user import User
from routes.services.cache_service import (
    ADMIN_COMPANIES_PREFIX,
    ADMIN_JOBS_PREFIX,
    ADMIN_STUDENTS_PREFIX,
    STUDENT_DRIVES_PREFIX,
    cached,
    clear_cache,
)
from routes.services.pdf_service import create_monthly_report_pdf
from routes.services.report_service import (
    admin_stats,
    application_funnel,
    monthly_activity_report,
    placement_trend,
)
from utils.decorators import role_required
from utils.validators import parse_bool

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard", methods=["GET"])
@role_required("admin")
def admin_dashboard():
    return jsonify({
        "message": "Admin dashboard",
        "stats": admin_stats(),
        "analytics": {
            "trend": placement_trend(),
            "funnel": application_funnel(),
        },
    }), 200


@admin_bp.route("/users", methods=["GET"])
@role_required("admin")
def list_users():
    role_filter = request.args.get("role", "").strip()
    search = request.args.get("q", "").strip()
    query = User.query.order_by(User.created_at.desc())

    if role_filter:
        query = query.filter_by(role=role_filter)
    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )

    users = query.all()
    return jsonify({
        "users": [user.to_dict() for user in users]
    }), 200


@admin_bp.route("/users/<int:user_id>/status", methods=["PATCH"])
@role_required("admin")
def update_user_status(user_id):
    user = User.query.get_or_404(user_id)
    payload = request.get_json(silent=True) or {}

    if "is_active" not in payload:
        return jsonify({"message": "is_active is required"}), 400

    is_active = parse_bool(payload["is_active"])
    if is_active is None:
        return jsonify({"message": "is_active must be true or false"}), 400

    user.is_active = is_active
    db.session.commit()
    clear_cache(ADMIN_STUDENTS_PREFIX, ADMIN_COMPANIES_PREFIX)

    return jsonify({
        "message": "User status updated",
        "user": user.to_dict(),
    }), 200


@admin_bp.route("/companies", methods=["GET"])
@role_required("admin")
@cached(timeout=300)
def list_companies():
    approved_filter = request.args.get("approved", "")
    search = request.args.get("q", "").strip()
    query = Company.query.order_by(Company.id.desc())

    if approved_filter in {"true", "false"}:
        query = query.filter_by(approved=(approved_filter == "true"))
    if search:
        query = query.filter(
            (Company.company_name.ilike(f"%{search}%")) |
            (Company.industry.ilike(f"%{search}%")) |
            (Company.location.ilike(f"%{search}%"))
        )

    companies = query.all()
    return jsonify({
        "companies": [company.to_dict() for company in companies]
    }), 200


@admin_bp.route("/companies/<int:company_id>/approve", methods=["PATCH"])
@role_required("admin")
def approve_company(company_id):
    company = Company.query.get_or_404(company_id)
    payload = request.get_json(silent=True) or {}

    approved = parse_bool(payload.get("approved"), True)
    if approved is None:
        return jsonify({"message": "approved must be true or false"}), 400

    company.approved = approved
    company.rejection_reason = payload.get("rejection_reason")
    db.session.commit()
    clear_cache(ADMIN_COMPANIES_PREFIX)

    company_email = company.contact_email or (company.user.email if company.user else None)
    if company_email:
        from tasks import notify_company_approval
        notify_company_approval.delay(company_email, company.company_name, approved, company.rejection_reason)

    return jsonify({
        "message": "Company approval updated",
        "company": company.to_dict(),
    }), 200


@admin_bp.route("/companies/<int:company_id>", methods=["DELETE"])
@role_required("admin")
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    user = company.user
    if user:
        db.session.delete(user)
    else:
        db.session.delete(company)
    db.session.commit()
    clear_cache(ADMIN_COMPANIES_PREFIX, ADMIN_JOBS_PREFIX, STUDENT_DRIVES_PREFIX)

    return jsonify({"message": "Company removed"}), 200


@admin_bp.route("/companies/<int:company_id>/reports/monthly", methods=["POST"])
@role_required("admin")
def trigger_company_monthly_report(company_id):
    Company.query.get_or_404(company_id)

    from tasks import generate_company_monthly_report
    task = generate_company_monthly_report.delay(company_id)
    return jsonify({"message": "Company report generation started", "task_id": task.id}), 202


@admin_bp.route("/jobs", methods=["GET"])
@role_required("admin")
@cached(timeout=300)
def list_jobs():
    approved_filter = request.args.get("approved", "")
    search = request.args.get("q", "").strip()
    query = JobPosition.query.order_by(JobPosition.created_at.desc())

    if approved_filter in {"true", "false"}:
        query = query.filter_by(approved=(approved_filter == "true"))
    if search:
        query = query.filter(
            (JobPosition.title.ilike(f"%{search}%")) |
            (JobPosition.skills_required.ilike(f"%{search}%")) |
            (JobPosition.location.ilike(f"%{search}%"))
        )

    jobs = query.all()
    return jsonify({
        "jobs": [job.to_dict() for job in jobs]
    }), 200


@admin_bp.route("/jobs/<int:job_id>/approve", methods=["PATCH"])
@role_required("admin")
def approve_job(job_id):
    job = JobPosition.query.get_or_404(job_id)
    payload = request.get_json(silent=True) or {}

    approved = parse_bool(payload.get("approved"), True)
    if approved is None:
        return jsonify({"message": "approved must be true or false"}), 400

    job.approved = approved
    job.status = payload.get("status") or ("Approved" if approved else "Rejected")
    db.session.commit()
    clear_cache(ADMIN_JOBS_PREFIX, STUDENT_DRIVES_PREFIX)

    company = job.company
    company_email = company.contact_email or (company.user.email if company.user else None)
    if company_email:
        from tasks import notify_job_approval
        notify_job_approval.delay(company_email, company.company_name, job.title, approved)

    return jsonify({
        "message": "Job approval updated",
        "job": job.to_dict(),
    }), 200


@admin_bp.route("/jobs/<int:job_id>", methods=["DELETE"])
@role_required("admin")
def delete_job(job_id):
    job = JobPosition.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    clear_cache(ADMIN_JOBS_PREFIX, STUDENT_DRIVES_PREFIX)

    return jsonify({"message": "Placement drive removed"}), 200


@admin_bp.route("/applications", methods=["GET"])
@role_required("admin")
def list_applications():
    status_filter = request.args.get("status", "").strip()
    query = Application.query.order_by(Application.applied_at.desc())

    if status_filter:
        query = query.filter_by(status=status_filter)

    applications = query.all()
    return jsonify({
        "applications": [application.to_dict() for application in applications]
    }), 200


@admin_bp.route("/students", methods=["GET"])
@role_required("admin")
@cached(timeout=300)
def list_students():
    search = request.args.get("q", "").strip()
    query = Student.query.join(User).order_by(Student.id.desc())

    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (Student.college.ilike(f"%{search}%")) |
            (Student.branch.ilike(f"%{search}%"))
        )

    return jsonify({
        "students": [student.to_dict() for student in query.all()]
    }), 200


@admin_bp.route("/placements", methods=["GET"])
@role_required("admin")
def list_placements():
    placements = Placement.query.order_by(Placement.placed_at.desc()).all()
    return jsonify({
        "placements": [placement.to_dict() for placement in placements]
    }), 200


@admin_bp.route("/reports/monthly", methods=["GET"])
@role_required("admin")
def monthly_report():
    return jsonify({
        "html": monthly_activity_report(),
        "stats": admin_stats()
    }), 200


@admin_bp.route("/reports/monthly/pdf", methods=["POST"])
@role_required("admin")
def monthly_report_pdf():
    filename, path = create_monthly_report_pdf(admin_stats())
    return jsonify({
        "message": "Monthly report PDF generated",
        "filename": filename,
        "path": path
    }), 201


@admin_bp.route("/settings/reminder-time", methods=["GET", "PATCH"])
@role_required("admin")
def reminder_time_settings():
    settings = ReminderSettings.get_singleton()

    if request.method == "GET":
        return jsonify({"settings": settings.to_dict()}), 200

    payload = request.get_json(silent=True) or {}
    if "deadline_reminder_hour" in payload:
        hour = payload.get("deadline_reminder_hour")
        if not isinstance(hour, int) or not (0 <= hour <= 23):
            return jsonify({"message": "deadline_reminder_hour must be an integer between 0 and 23"}), 400
        settings.deadline_reminder_hour = hour

    if "deadline_reminder_minute" in payload:
        minute = payload.get("deadline_reminder_minute")
        if not isinstance(minute, int) or not (0 <= minute <= 59):
            return jsonify({"message": "deadline_reminder_minute must be an integer between 0 and 59"}), 400
        settings.deadline_reminder_minute = minute

    db.session.commit()
    return jsonify({"message": "Reminder time updated", "settings": settings.to_dict()}), 200
