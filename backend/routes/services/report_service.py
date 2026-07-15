import csv
import os
from calendar import monthrange
from datetime import datetime, timezone

from flask import current_app

from models.application import Application
from models.company import Company
from models.job import JobPosition
from models.placement import Placement
from models.student import Student
from models.user import User


def _month_bounds(month=None, year=None):
    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def admin_stats(month=None, year=None):
    start, end = _month_bounds(month, year)
    return {
        "total_users": User.query.count(),
        "total_students": Student.query.count(),
        "total_companies": Company.query.count(),
        "total_jobs": JobPosition.query.count(),
        "total_applications": Application.query.count(),
        "total_placements": Placement.query.count(),
        "pending_companies": Company.query.filter_by(approved=False).count(),
        "pending_jobs": JobPosition.query.filter_by(approved=False).count(),
        "selected_students": Application.query.filter(Application.status.in_(["Selected", "Placed"])).count(),
        "drives_this_month": JobPosition.query.filter(
            JobPosition.created_at >= start, JobPosition.created_at <= end
        ).count(),
        "applications_this_month": Application.query.filter(
            Application.applied_at >= start, Application.applied_at <= end
        ).count(),
        "placements_this_month": Placement.query.filter(
            Placement.placed_at >= start, Placement.placed_at <= end
        ).count(),
        "selected_this_month": Application.query.filter(
            Application.applied_at >= start,
            Application.applied_at <= end,
            Application.status.in_(["Selected", "Placed"]),
        ).count(),
    }


def monthly_activity_report(month=None, year=None):
    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year
    stats = admin_stats(month, year)
    period_label = datetime(year, month, 1).strftime("%B %Y")
    rows = [
        ("Report month", period_label),
        ("Placement drives conducted", stats["drives_this_month"]),
        ("Students applied", stats["applications_this_month"]),
        ("Students selected", stats["selected_this_month"]),
        ("Placements confirmed", stats["placements_this_month"]),
    ]
    body = "".join(f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in rows)
    return f"""
    <html>
      <body>
        <h1>Placement Portal Monthly Activity Report</h1>
        <table border="1" cellpadding="8" cellspacing="0">{body}</table>
      </body>
    </html>
    """


def company_monthly_report(company_id, month=None, year=None):
    company = Company.query.get(company_id)
    if not company:
        return None

    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year
    start, end = _month_bounds(month, year)

    drives_this_month = JobPosition.query.filter(
        JobPosition.company_id == company_id,
        JobPosition.created_at >= start,
        JobPosition.created_at <= end,
    ).count()
    applications_this_month = (
        Application.query
        .join(JobPosition)
        .filter(
            JobPosition.company_id == company_id,
            Application.applied_at >= start,
            Application.applied_at <= end,
        )
        .count()
    )
    placements_this_month = Placement.query.filter(
        Placement.company_id == company_id,
        Placement.placed_at >= start,
        Placement.placed_at <= end,
    ).count()

    period_label = datetime(year, month, 1).strftime("%B %Y")
    rows = [
        ("Company", company.company_name),
        ("Report month", period_label),
        ("Drives posted", drives_this_month),
        ("Applications received", applications_this_month),
        ("Placements confirmed", placements_this_month),
    ]
    body = "".join(f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in rows)
    return f"""
    <html>
      <body>
        <h1>{company.company_name} &mdash; Monthly Activity Report</h1>
        <table border="1" cellpadding="8" cellspacing="0">{body}</table>
      </body>
    </html>
    """


def placement_trend(months=6):
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month

    month_pairs = []
    for offset in range(months - 1, -1, -1):
        m = month - offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        month_pairs.append((y, m))

    labels, counts = [], []
    for y, m in month_pairs:
        start, end = _month_bounds(m, y)
        count = Placement.query.filter(Placement.placed_at >= start, Placement.placed_at <= end).count()
        labels.append(start.strftime("%b %Y"))
        counts.append(count)

    return {"labels": labels, "counts": counts}


def application_funnel():
    statuses = ["Applied", "Shortlisted", "Interview", "Selected", "Placed"]
    return {
        "labels": statuses,
        "counts": [Application.query.filter_by(status=status).count() for status in statuses],
    }


def export_student_applications_csv(student):
    export_dir = os.path.join(current_app.instance_path, "exports")
    os.makedirs(export_dir, exist_ok=True)
    filename = f"student_{student.id}_applications.csv"
    path = os.path.join(export_dir, filename)

    applications = (
        Application.query
        .filter_by(student_id=student.id)
        .order_by(Application.applied_at.desc())
        .all()
    )

    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Student ID",
            "Company Name",
            "Drive Title",
            "Application Status",
            "Applied At",
            "Interview At",
        ])
        for application in applications:
            writer.writerow([
                student.id,
                application.job.company.company_name if application.job and application.job.company else "",
                application.job.title if application.job else "",
                application.status,
                application.applied_at.isoformat() if application.applied_at else "",
                application.interview_at.isoformat() if application.interview_at else "",
            ])

    return filename, path


def export_company_applications_csv(company):
    export_dir = os.path.join(current_app.instance_path, "exports")
    os.makedirs(export_dir, exist_ok=True)
    filename = f"company_{company.id}_applications.csv"
    path = os.path.join(export_dir, filename)

    applications = (
        Application.query
        .join(JobPosition)
        .filter(JobPosition.company_id == company.id)
        .order_by(Application.applied_at.desc())
        .all()
    )

    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Company ID",
            "Student Name",
            "Drive Title",
            "Application Status",
            "Applied At",
            "Interview At",
        ])
        for application in applications:
            writer.writerow([
                company.id,
                application.student.user.name if application.student and application.student.user else "",
                application.job.title if application.job else "",
                application.status,
                application.applied_at.isoformat() if application.applied_at else "",
                application.interview_at.isoformat() if application.interview_at else "",
            ])

    return filename, path
