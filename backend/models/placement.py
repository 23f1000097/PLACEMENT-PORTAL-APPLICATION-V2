from datetime import datetime, timezone

from extensions import db


class Placement(db.Model):
    __tablename__ = "placements"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"))

    job_id = db.Column(db.Integer, db.ForeignKey("job_positions.id"))

    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"))

    company_name = db.Column(db.String(150))

    job_title = db.Column(db.String(150))

    package = db.Column(db.Float)

    joining_date = db.Column(db.Date)

    placed_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    company = db.relationship("Company", backref="placements")
    job = db.relationship("JobPosition", backref="placements")
    application = db.relationship("Application", backref="placement", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "company_id": self.company_id,
            "job_id": self.job_id,
            "application_id": self.application_id,
            "student_name": self.student.user.name if self.student and self.student.user else None,
            "company_name": self.company_name,
            "job_title": self.job_title,
            "package": self.package,
            "joining_date": self.joining_date.isoformat() if self.joining_date else None,
            "placed_at": self.placed_at.isoformat() if self.placed_at else None
        }
