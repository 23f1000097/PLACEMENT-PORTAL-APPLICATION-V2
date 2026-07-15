import logging
import os
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app import app
from celery_app import celery
from models.application import Application
from models.company import Company
from models.job import JobPosition
from models.settings import ReminderSettings
from models.student import Student
from routes.services.pdf_service import create_monthly_report_pdf
from routes.services.report_service import (
    admin_stats,
    company_monthly_report,
    export_company_applications_csv,
    export_student_applications_csv,
    monthly_activity_report,
)
from utils.email import send_email

logger = logging.getLogger(__name__)


def safe_send_email(subject, body, recipients, html=None, attachments=None):
    """Send an email, but never fail the calling task just because SMTP
    credentials haven't been configured yet in this environment."""
    try:
        return send_email(subject, body, recipients, html=html, attachments=attachments)
    except RuntimeError as exc:
        logger.warning("Email not sent (SMTP not configured): %s", exc)
        return False


@celery.task(name="tasks.send_daily_deadline_reminders")
def send_daily_deadline_reminders():
    with app.app_context():
        settings = ReminderSettings.get_singleton()
        now_local = datetime.now(ZoneInfo("Asia/Kolkata"))
        target_minutes = settings.deadline_reminder_hour * 60 + settings.deadline_reminder_minute
        now_minutes = now_local.hour * 60 + now_local.minute
        if (now_minutes - target_minutes) % (24 * 60) >= 5:
            return {"skipped": True, "reason": "not yet the configured reminder time"}

        sent = []

        upcoming_date = date.today() + timedelta(days=1)
        jobs = (
            JobPosition.query
            .filter(JobPosition.approved.is_(True), JobPosition.last_date == upcoming_date)
            .all()
        )
        for job in jobs:
            applied_student_ids = {a.student_id for a in Application.query.filter_by(job_id=job.id).all()}
            eligible_students = Student.query.filter(~Student.id.in_(applied_student_ids)).all()
            for student in eligible_students:
                if not student.user or not student.user.email:
                    continue
                subject = f"Deadline tomorrow: {job.title}"
                body = (
                    f"Hi {student.user.name},\n\n"
                    f"The application deadline for '{job.title}' is tomorrow ({job.last_date.isoformat()}). "
                    "Apply now if you're interested and eligible.\n\n"
                    "Best regards,\nPlacement Portal Team"
                )
                if safe_send_email(subject, body, [student.user.email]):
                    sent.append({"type": "deadline", "student_id": student.id, "job_id": job.id})

        window_start = datetime.now(timezone.utc)
        window_end = window_start + timedelta(hours=24)
        interview_applications = (
            Application.query
            .filter(Application.interview_at.isnot(None))
            .filter(Application.interview_at >= window_start)
            .filter(Application.interview_at <= window_end)
            .all()
        )
        for application in interview_applications:
            student = application.student
            if not student or not student.user or not student.user.email:
                continue
            job = application.job
            company_name = job.company.company_name if job and job.company else "the company"
            job_title = job.title if job else "your application"
            subject = f"Interview reminder: {job_title}"
            body = (
                f"Hi {student.user.name},\n\n"
                f"This is a reminder that your interview for '{job_title}' at {company_name} "
                f"is scheduled at {application.interview_at.isoformat()}. Good luck!\n\n"
                "Best regards,\nPlacement Portal Team"
            )
            if safe_send_email(subject, body, [student.user.email]):
                sent.append({"type": "interview", "student_id": student.id, "application_id": application.id})

        return {"reminders_sent": len(sent), "details": sent}


@celery.task(name="tasks.generate_monthly_activity_report")
def generate_monthly_activity_report():
    with app.app_context():
        html = monthly_activity_report()
        filename, path = create_monthly_report_pdf(admin_stats())
        admin_email = os.getenv("ADMIN_EMAIL", "admin@placement.com")
        subject = f"Monthly Activity Report — {datetime.now(timezone.utc).strftime('%B %Y')}"
        body = "Please find this month's placement activity report attached."
        emailed = safe_send_email(subject, body, [admin_email], html=html, attachments=[(filename, path)])
        return {"emailed": emailed, "filename": filename, "path": path}


@celery.task(name="tasks.generate_company_monthly_report")
def generate_company_monthly_report(company_id):
    with app.app_context():
        company = Company.query.get(company_id)
        if not company:
            return {"error": "Company not found"}

        recipient = company.contact_email or (company.user.email if company.user else None)
        if not recipient:
            return {"error": "No recipient email on file for this company"}

        html = company_monthly_report(company_id)
        subject = f"Your Monthly Placement Activity Report — {datetime.now(timezone.utc).strftime('%B %Y')}"
        body = "Please find this month's placement activity summary for your company below."
        emailed = safe_send_email(subject, body, [recipient], html=html)
        return {"emailed": emailed}


@celery.task(name="tasks.notify_student_application")
def notify_student_application(student_email, student_name, job_title, company_name):
    with app.app_context():
        subject = f"Application received for {job_title}"
        body = (
            f"Hi {student_name},\n\n"
            f"Your application for the job '{job_title}' at {company_name} has been submitted successfully. "
            "The company will review your application and contact you if you are shortlisted.\n\n"
            "Best regards,\nPlacement Portal Team"
        )
        sent = safe_send_email(subject, body, [student_email])
        return {"sent_to": student_email, "emailed": sent}


@celery.task(name="tasks.notify_company_application")
def notify_company_application(company_email, company_name, student_name, job_title):
    with app.app_context():
        subject = f"New application for {job_title}"
        body = (
            f"Hi {company_name},\n\n"
            f"{student_name} has applied for the job '{job_title}'.\n"
            "Please review the student's profile and take the next action (shortlist, schedule interview, or reject).\n\n"
            "Best regards,\nPlacement Portal Team"
        )
        sent = safe_send_email(subject, body, [company_email])
        return {"sent_to": company_email, "emailed": sent}


@celery.task(name="tasks.notify_student_status_update")
def notify_student_status_update(student_email, student_name, job_title, status, company_name, interview_at=None):
    with app.app_context():
        subject = f"Your application status has been updated: {status}"
        if status == 'Interview':
            if interview_at:
                scheduled = datetime.fromisoformat(interview_at).strftime("%A, %d %B %Y at %I:%M %p")
                status_text = f"Your application for '{job_title}' at {company_name} is now at Interview stage. Your interview is scheduled for {scheduled}. Please check your dashboard for any further details."
            else:
                status_text = f"Your application for '{job_title}' at {company_name} is now at Interview stage. Please check your dashboard for interview timing and next steps."
        elif status == 'Selected':
            status_text = f"Congratulations! You've been selected for '{job_title}' at {company_name}. Please follow up with the company for the next steps."
        elif status == 'Rejected':
            status_text = f"We are sorry to let you know that your application for '{job_title}' at {company_name} was not selected."
        else:
            status_text = f"The status of your application for '{job_title}' at {company_name} is now '{status}'."

        body = (
            f"Hi {student_name},\n\n"
            f"{status_text}\n\n"
            "Best regards,\nPlacement Portal Team"
        )
        sent = safe_send_email(subject, body, [student_email])
        return {"sent_to": student_email, "emailed": sent}


@celery.task(name="tasks.notify_company_approval")
def notify_company_approval(company_email, company_name, approved, rejection_reason=None):
    with app.app_context():
        if approved:
            subject = "Your company registration has been approved"
            body = (
                f"Hi {company_name},\n\n"
                "Your company registration on the Placement Portal has been approved by the admin. "
                "You can now log in, complete your profile, and start posting placement drives.\n\n"
                "Best regards,\nPlacement Portal Team"
            )
        else:
            subject = "Your company registration was not approved"
            reason_text = f" Reason: {rejection_reason}" if rejection_reason else ""
            body = (
                f"Hi {company_name},\n\n"
                f"Your company registration on the Placement Portal was not approved by the admin.{reason_text}\n\n"
                "Best regards,\nPlacement Portal Team"
            )
        sent = safe_send_email(subject, body, [company_email])
        return {"sent_to": company_email, "emailed": sent}


@celery.task(name="tasks.notify_job_approval")
def notify_job_approval(company_email, company_name, job_title, approved):
    with app.app_context():
        if approved:
            subject = f"Your placement drive '{job_title}' has been approved"
            body = (
                f"Hi {company_name},\n\n"
                f"Your placement drive '{job_title}' has been approved by the admin and is now visible to "
                "eligible students.\n\n"
                "Best regards,\nPlacement Portal Team"
            )
        else:
            subject = f"Your placement drive '{job_title}' was not approved"
            body = (
                f"Hi {company_name},\n\n"
                f"Your placement drive '{job_title}' was not approved by the admin. Please review the drive "
                "details and get in touch if you have questions.\n\n"
                "Best regards,\nPlacement Portal Team"
            )
        sent = safe_send_email(subject, body, [company_email])
        return {"sent_to": company_email, "emailed": sent}


@celery.task(name="tasks.export_student_applications")
def export_student_applications(student_id):
    with app.app_context():
        student = Student.query.get(student_id)
        if not student:
            return {"error": "Student not found"}
        filename, path = export_student_applications_csv(student)

        if student.user and student.user.email:
            safe_send_email(
                "Your application export is ready",
                f"Hi {student.user.name},\n\nYour CSV export of applications ({filename}) is ready to download from your dashboard.\n\nBest regards,\nPlacement Portal Team",
                [student.user.email],
            )

        return {"student_id": student_id, "filename": filename, "path": path}


@celery.task(name="tasks.export_company_applications")
def export_company_applications(company_id):
    with app.app_context():
        company = Company.query.get(company_id)
        if not company:
            return {"error": "Company not found"}
        filename, path = export_company_applications_csv(company)

        recipient = company.contact_email or (company.user.email if company.user else None)
        if recipient:
            safe_send_email(
                "Your application export is ready",
                f"Hi {company.company_name},\n\nYour CSV export of applications ({filename}) is ready to download from your dashboard.\n\nBest regards,\nPlacement Portal Team",
                [recipient],
            )

        return {"company_id": company_id, "filename": filename, "path": path}
