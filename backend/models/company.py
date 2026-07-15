from extensions import db


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    company_name = db.Column(db.String(150), nullable=False)

    industry = db.Column(db.String(120))

    hr_contact = db.Column(db.String(120))

    contact_email = db.Column(db.String(150))

    phone = db.Column(db.String(30))

    website = db.Column(db.String(200))

    location = db.Column(db.String(150))

    description = db.Column(db.Text)

    logo = db.Column(db.String(255))

    approved = db.Column(db.Boolean, default=False)

    rejection_reason = db.Column(db.Text)

    jobs = db.relationship(
        "JobPosition",
        backref="company",
        lazy=True,
        cascade="all, delete"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "industry": self.industry,
            "hr_contact": self.hr_contact,
            "contact_email": self.contact_email,
            "phone": self.phone,
            "website": self.website,
            "location": self.location,
            "description": self.description,
            "logo": self.logo,
            "is_active": self.user.is_active if self.user else None,
            "rejection_reason": self.rejection_reason,
            "approved": self.approved
        }
