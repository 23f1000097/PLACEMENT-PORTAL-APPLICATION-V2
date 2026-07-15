from datetime import datetime, timezone

from extensions import db


class JobPosition(db.Model):
    __tablename__ = "job_positions"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id"),
        nullable=False
    )

    title = db.Column(db.String(150), nullable=False)

    description = db.Column(db.Text, nullable=False)

    location = db.Column(db.String(100))

    job_type = db.Column(db.String(50))

    salary = db.Column(db.Float)

    skills_required = db.Column(db.Text)

    benefits = db.Column(db.Text)

    minimum_cgpa = db.Column(db.Float)

    eligibility_branch = db.Column(db.String(150))

    eligibility_year = db.Column(db.Integer)

    vacancies = db.Column(db.Integer)

    last_date = db.Column(db.Date)

    approved = db.Column(db.Boolean, default=False)

    status = db.Column(db.String(30), default="Pending")

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    applications = db.relationship(
        "Application",
        backref="job",
        lazy=True,
        cascade="all, delete"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "job_type": self.job_type,
            "salary": self.salary,
            "skills_required": self.skills_required,
            "benefits": self.benefits,
            "minimum_cgpa": self.minimum_cgpa,
            "eligibility_branch": self.eligibility_branch,
            "eligibility_year": self.eligibility_year,
            "vacancies": self.vacancies,
            "last_date": self.last_date.isoformat() if self.last_date else None,
            "approved": self.approved,
            "status": self.status,
            "company_name": self.company.company_name if self.company else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
