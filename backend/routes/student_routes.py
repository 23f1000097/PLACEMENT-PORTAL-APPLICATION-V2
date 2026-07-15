import os

from flask import Blueprint, current_app, g, jsonify, request, send_file, send_from_directory

from extensions import db
from models.application import Application
from models.company import Company
from models.job import JobPosition
from models.placement import Placement
from routes.services.cache_service import cached
from routes.services.eligibility_service import student_matches_job
from utils.decorators import role_required
from utils.helper import save_file
from utils.validators import allowed_file, validate_positive_number, validate_year

student_bp = Blueprint("student", __name__)


@student_bp.route("/dashboard", methods=["GET"])
@role_required("student")
def dashboard():
    student = g.current_user.student
    if not student:
        return jsonify({"message": "Student profile not found"}), 404

    drives = (
        JobPosition.query
        .filter_by(approved=True)
        .filter(JobPosition.status.in_(["Approved", "Active"]))
        .order_by(JobPosition.created_at.desc())
        .all()
    )
    applications = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()
    placements = Placement.query.filter_by(student_id=student.id).order_by(Placement.placed_at.desc()).all()

    return jsonify({
        "student": student.to_dict(),
        "approved_drives": [drive.to_dict() for drive in drives],
        "applications": [application.to_dict() for application in applications],
        "placements": [placement.to_dict() for placement in placements],
    }), 200


@student_bp.route("/profile", methods=["GET", "PATCH"])
@role_required("student")
def profile():
    student = g.current_user.student
    if not student:
        return jsonify({"message": "Student profile not found"}), 404

    if request.method == "GET":
        return jsonify({"student": student.to_dict()}), 200

    payload = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})

    if payload.get("cgpa") not in (None, ""):
        cgpa, err = validate_positive_number(payload["cgpa"], field_name="CGPA")
        if err or cgpa > 10:
            return jsonify({"message": err or "CGPA must be between 0 and 10"}), 400
        payload["cgpa"] = cgpa

    if payload.get("passing_year") not in (None, ""):
        passing_year, err = validate_year(payload["passing_year"], field_name="Passing year")
        if err:
            return jsonify({"message": err}), 400
        payload["passing_year"] = passing_year

    for field in [
        "college", "phone", "degree", "branch", "specialization", "cgpa",
        "passing_year", "skills", "experience"
    ]:
        if field in payload:
            setattr(student, field, payload[field])

    if "name" in payload:
        g.current_user.name = payload["name"]

    resume = request.files.get("resume")
    if resume:
        if not allowed_file(resume.filename, current_app.config["ALLOWED_RESUME_EXTENSIONS"]):
            return jsonify({"message": "Resume must be pdf, doc, or docx"}), 400
        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "resumes")
        student.resume = save_file(resume, upload_dir)

    db.session.commit()
    return jsonify({"message": "Student profile updated", "student": student.to_dict()}), 200


@student_bp.route("/drives", methods=["GET"])
@role_required("student")
@cached(timeout=300)
def drives():
    student = g.current_user.student
    if not student:
        return jsonify({"message": "Student profile not found"}), 404

    search = request.args.get("q", "").strip()
    eligible_only = request.args.get("eligible_only", "false").lower() == "true"
    query = (
        JobPosition.query
        .join(Company, JobPosition.company_id == Company.id)
        .filter(JobPosition.approved == True)  # noqa: E712
        .filter(JobPosition.status.in_(["Approved", "Active"]))
        .order_by(JobPosition.created_at.desc())
    )
    if search:
        query = query.filter(
            (JobPosition.title.ilike(f"%{search}%")) |
            (JobPosition.skills_required.ilike(f"%{search}%")) |
            (JobPosition.location.ilike(f"%{search}%")) |
            (Company.company_name.ilike(f"%{search}%"))
        )

    rows = []
    for job in query.all():
        eligible, reasons = student_matches_job(student, job)
        if eligible_only and not eligible:
            continue
        data = job.to_dict()
        data["eligible"] = eligible
        data["eligibility_reasons"] = reasons
        rows.append(data)

    return jsonify({"drives": rows}), 200


@student_bp.route("/drives/<int:job_id>/apply", methods=["POST"])
@role_required("student")
def apply_to_drive(job_id):
    student = g.current_user.student
    if not student:
        return jsonify({"message": "Student profile not found"}), 404

    job = JobPosition.query.get_or_404(job_id)
    existing = Application.query.filter_by(student_id=student.id, job_id=job.id).first()
    if existing:
        return jsonify({"message": "Already applied to this drive", "application": existing.to_dict()}), 409

    eligible, reasons = student_matches_job(student, job)
    if not eligible:
        return jsonify({"message": "Student is not eligible for this drive", "reasons": reasons}), 400

    application = Application(student_id=student.id, job_id=job.id)
    db.session.add(application)
    db.session.commit()

    company = job.company
    student_email = student.user.email if student.user else None
    student_name = student.user.name if student.user else 'Student'
    company_email = company.contact_email or (company.user.email if company.user else None)
    company_name = company.company_name if company else 'Company'

    from tasks import notify_company_application, notify_student_application

    if student_email:
        notify_student_application.delay(student_email, student_name, job.title, company_name)
    if company_email:
        notify_company_application.delay(company_email, company_name, student_name, job.title)

    return jsonify({"message": "Application submitted", "application": application.to_dict()}), 201


@student_bp.route("/applications", methods=["GET"])
@role_required("student")
def applications():
    student = g.current_user.student
    if not student:
        return jsonify({"message": "Student profile not found"}), 404

    rows = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()
    return jsonify({"applications": [row.to_dict() for row in rows]}), 200


@student_bp.route("/placements", methods=["GET"])
@role_required("student")
def placements():
    student = g.current_user.student
    if not student:
        return jsonify({"message": "Student profile not found"}), 404

    rows = Placement.query.filter_by(student_id=student.id).order_by(Placement.placed_at.desc()).all()
    return jsonify({"placements": [row.to_dict() for row in rows]}), 200


@student_bp.route("/applications/export", methods=["POST"])
@role_required("student")
def export_applications():
    student = g.current_user.student
    if not student:
        return jsonify({"message": "Student profile not found"}), 404

    from tasks import export_student_applications
    task = export_student_applications.delay(student.id)
    return jsonify({"message": "Export started", "task_id": task.id}), 202


@student_bp.route("/applications/export/<task_id>", methods=["GET"])
@role_required("student")
def export_applications_status(task_id):
    student = g.current_user.student
    if not student:
        return jsonify({"message": "Student profile not found"}), 404

    from celery_app import celery
    result = celery.AsyncResult(task_id)

    if result.state == "FAILURE":
        return jsonify({"state": result.state, "error": str(result.result)}), 500
    if result.state != "SUCCESS":
        return jsonify({"state": result.state}), 202

    payload = result.result or {}
    if payload.get("student_id") != student.id:
        return jsonify({"message": "Unauthorized"}), 403

    path = payload.get("path")
    if not path or not os.path.exists(path):
        return jsonify({"message": "Export file not found"}), 404

    if request.args.get("download") == "true":
        return send_file(path, as_attachment=True, download_name=payload.get("filename"))

    return jsonify({"state": result.state, "filename": payload.get("filename")}), 200


@student_bp.route("/applications/<int:application_id>/offer-letter", methods=["GET"])
@role_required("student")
def download_offer_letter(application_id):
    student = g.current_user.student
    if not student:
        return jsonify({"message": "Student profile not found"}), 404

    application = Application.query.filter_by(id=application_id, student_id=student.id).first_or_404()
    if not application.offer_letter:
        return jsonify({"message": "No offer letter available for this application"}), 404

    directory = os.path.join(current_app.config["UPLOAD_FOLDER"], "offer_letters")
    return send_from_directory(directory, application.offer_letter, as_attachment=True)
