import os

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import func

from extensions import db
from models.application import Application
from models.job import JobPosition
from routes.services.cache_service import (
    ADMIN_JOBS_PREFIX,
    STUDENT_DRIVES_PREFIX,
    clear_cache,
)
from utils.decorators import role_required
from utils.helper import save_file
from utils.validators import (
    allowed_file,
    parse_date,
    require_fields,
    validate_positive_number,
    validate_year,
)

company_bp = Blueprint("company", __name__)


def validate_job_numeric_fields(payload):
    """Coerce/validate numeric job fields. Returns (cleaned_payload, error_message)."""
    cleaned = dict(payload)

    if cleaned.get("salary") not in (None, ""):
        salary, err = validate_positive_number(cleaned["salary"], field_name="Salary")
        if err:
            return None, err
        cleaned["salary"] = salary

    if cleaned.get("vacancies") not in (None, ""):
        vacancies, err = validate_positive_number(cleaned["vacancies"], allow_zero=False, field_name="Vacancies")
        if err:
            return None, err
        cleaned["vacancies"] = int(vacancies)

    if cleaned.get("minimum_cgpa") not in (None, ""):
        minimum_cgpa, err = validate_positive_number(cleaned["minimum_cgpa"], field_name="Minimum CGPA")
        if err:
            return None, err
        if minimum_cgpa > 10:
            return None, "Minimum CGPA must be between 0 and 10"
        cleaned["minimum_cgpa"] = minimum_cgpa

    if cleaned.get("eligibility_year") not in (None, ""):
        eligibility_year, err = validate_year(cleaned["eligibility_year"], field_name="Eligibility year")
        if err:
            return None, err
        cleaned["eligibility_year"] = eligibility_year

    return cleaned, None


def require_approved_company():
    company = g.current_user.company
    if not company:
        return None, (jsonify({"message": "Company profile not found"}), 404)
    if not company.approved:
        return None, (jsonify({"message": "Company is awaiting admin approval"}), 403)
    return company, None


@company_bp.route("/dashboard", methods=["GET"])
@role_required("company")
def dashboard():
    company, error = require_approved_company()
    if error:
        return error

    jobs = JobPosition.query.filter_by(company_id=company.id).order_by(JobPosition.created_at.desc()).all()
    application_count = (
        Application.query
        .join(JobPosition)
        .filter(JobPosition.company_id == company.id)
        .count()
    )
    shortlisted_count = (
        Application.query
        .join(JobPosition)
        .filter(JobPosition.company_id == company.id, Application.status.in_(["Shortlisted", "Interview", "Selected"]))
        .count()
    )

    return jsonify({
        "company": company.to_dict(),
        "jobs": [job.to_dict() for job in jobs],
        "stats": {
            "total_jobs": len(jobs),
            "total_applications": application_count,
            "shortlisted_candidates": shortlisted_count,
        }
    }), 200


@company_bp.route("/profile", methods=["GET", "PATCH"])
@role_required("company")
def profile():
    company = g.current_user.company
    if not company:
        return jsonify({"message": "Company profile not found"}), 404

    if request.method == "GET":
        return jsonify({"company": company.to_dict()}), 200

    payload = request.get_json(silent=True) or {}
    for field in [
        "company_name", "industry", "hr_contact", "contact_email", "phone",
        "website", "location", "description", "logo"
    ]:
        if field in payload:
            setattr(company, field, payload[field])
    db.session.commit()
    return jsonify({"message": "Company profile updated", "company": company.to_dict()}), 200


@company_bp.route("/jobs", methods=["GET", "POST"])
@role_required("company")
def jobs():
    company, error = require_approved_company()
    if error:
        return error

    if request.method == "GET":
        rows = JobPosition.query.filter_by(company_id=company.id).order_by(JobPosition.created_at.desc()).all()
        return jsonify({"jobs": [job.to_dict() for job in rows]}), 200

    payload = request.get_json(silent=True) or {}
    missing = require_fields(payload, ["title", "description"])
    if missing:
        return jsonify({"message": f"Missing fields: {', '.join(missing)}"}), 400

    payload, err = validate_job_numeric_fields(payload)
    if err:
        return jsonify({"message": err}), 400

    duplicate = (
        JobPosition.query
        .filter(
            JobPosition.company_id == company.id,
            func.lower(JobPosition.title) == payload["title"].strip().lower(),
            JobPosition.status.notin_(["Rejected", "Deactivated"]),
        )
        .first()
    )
    if duplicate:
        return jsonify({"message": "You already have an active or pending posting with this title"}), 409

    job = JobPosition(
        company_id=company.id,
        title=payload["title"],
        description=payload["description"],
        location=payload.get("location"),
        job_type=payload.get("job_type"),
        salary=payload.get("salary"),
        skills_required=payload.get("skills_required"),
        benefits=payload.get("benefits"),
        minimum_cgpa=payload.get("minimum_cgpa"),
        eligibility_branch=payload.get("eligibility_branch"),
        eligibility_year=payload.get("eligibility_year"),
        vacancies=payload.get("vacancies"),
        last_date=parse_date(payload.get("last_date")),
        status="Pending",
        approved=False,
    )
    db.session.add(job)
    db.session.commit()
    clear_cache(STUDENT_DRIVES_PREFIX, ADMIN_JOBS_PREFIX)
    return jsonify({
        "message": "Placement drive created. Awaiting admin approval.",
        "job": job.to_dict()
    }), 201


@company_bp.route("/jobs/<int:job_id>", methods=["GET", "PATCH", "DELETE"])
@role_required("company")
def job_detail(job_id):
    company, error = require_approved_company()
    if error:
        return error

    job = JobPosition.query.filter_by(id=job_id, company_id=company.id).first_or_404()

    if request.method == "GET":
        return jsonify({"job": job.to_dict()}), 200

    if request.method == "DELETE":
        db.session.delete(job)
        db.session.commit()
        clear_cache(STUDENT_DRIVES_PREFIX, ADMIN_JOBS_PREFIX)
        return jsonify({"message": "Job deleted"}), 200

    payload = request.get_json(silent=True) or {}
    payload, err = validate_job_numeric_fields(payload)
    if err:
        return jsonify({"message": err}), 400

    if "status" in payload:
        new_status = payload["status"]
        company_settable = {"Active", "Deactivated"}
        if new_status not in company_settable:
            return jsonify({
                "message": f"Status must be one of: {', '.join(sorted(company_settable))}. "
                           "Approval status is managed by the admin."
            }), 400
        if not job.approved:
            return jsonify({"message": "Job must be approved by admin before it can be activated or deactivated"}), 400

    for field in [
        "title", "description", "location", "job_type", "salary", "skills_required",
        "benefits", "minimum_cgpa", "eligibility_branch", "eligibility_year",
        "vacancies", "status"
    ]:
        if field in payload:
            setattr(job, field, payload[field])
    if "last_date" in payload:
        job.last_date = parse_date(payload.get("last_date"))
    db.session.commit()
    clear_cache(STUDENT_DRIVES_PREFIX, ADMIN_JOBS_PREFIX)
    return jsonify({"message": "Job updated", "job": job.to_dict()}), 200


@company_bp.route("/jobs/<int:job_id>/applications", methods=["GET"])
@role_required("company")
def job_applications(job_id):
    company, error = require_approved_company()
    if error:
        return error

    job = JobPosition.query.filter_by(id=job_id, company_id=company.id).first_or_404()
    applications = Application.query.filter_by(job_id=job.id).order_by(Application.applied_at.desc()).all()
    return jsonify({
        "job": job.to_dict(),
        "applications": [application.to_dict() for application in applications]
    }), 200


@company_bp.route("/applications/<int:application_id>/offer-letter", methods=["POST"])
@role_required("company")
def upload_offer_letter(application_id):
    company, error = require_approved_company()
    if error:
        return error

    application = (
        Application.query
        .join(JobPosition)
        .filter(Application.id == application_id, JobPosition.company_id == company.id)
        .first_or_404()
    )

    file = request.files.get("offer_letter")
    if not file:
        return jsonify({"message": "offer_letter file is required"}), 400
    if not allowed_file(file.filename, current_app.config["ALLOWED_RESUME_EXTENSIONS"]):
        return jsonify({"message": "Offer letter must be pdf, doc, or docx"}), 400

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "offer_letters")
    application.offer_letter = save_file(file, upload_dir)
    db.session.commit()

    return jsonify({
        "message": "Offer letter uploaded",
        "application": application.to_dict()
    }), 200


@company_bp.route("/applications/export", methods=["POST"])
@role_required("company")
def export_applications():
    company, error = require_approved_company()
    if error:
        return error

    from tasks import export_company_applications
    task = export_company_applications.delay(company.id)
    return jsonify({"message": "Export started", "task_id": task.id}), 202


@company_bp.route("/applications/export/<task_id>", methods=["GET"])
@role_required("company")
def export_applications_status(task_id):
    company, error = require_approved_company()
    if error:
        return error

    from flask import send_file
    from celery_app import celery
    result = celery.AsyncResult(task_id)

    if result.state == "FAILURE":
        return jsonify({"state": result.state, "error": str(result.result)}), 500
    if result.state != "SUCCESS":
        return jsonify({"state": result.state}), 202

    payload = result.result or {}
    if payload.get("company_id") != company.id:
        return jsonify({"message": "Unauthorized"}), 403

    path = payload.get("path")
    if not path or not os.path.exists(path):
        return jsonify({"message": "Export file not found"}), 404

    if request.args.get("download") == "true":
        return send_file(path, as_attachment=True, download_name=payload.get("filename"))

    return jsonify({"state": result.state, "filename": payload.get("filename")}), 200
