from datetime import datetime, timezone

from extensions import db


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint("student_id", "job_id", name="uq_student_job_application"),
    )

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    job_id = db.Column(
        db.Integer,
        db.ForeignKey("job_positions.id"),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        default="Applied"
    )

    feedback = db.Column(db.Text)

    interview_at = db.Column(db.DateTime)

    offer_letter = db.Column(db.String(255))

    applied_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "job_id": self.job_id,
            "student_name": self.student.user.name if self.student and self.student.user else None,
            "job_title": self.job.title if self.job else None,
            "company_name": self.job.company.company_name if self.job and self.job.company else None,
            "status": self.status,
            "feedback": self.feedback,
            "interview_at": self.interview_at.isoformat() if self.interview_at else None,
            "offer_letter": self.offer_letter,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None
        }
