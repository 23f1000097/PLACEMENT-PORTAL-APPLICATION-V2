from extensions import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    college = db.Column(db.String(150))

    phone = db.Column(db.String(30))

    degree = db.Column(db.String(100))

    branch = db.Column(db.String(100))

    specialization = db.Column(db.String(100))

    cgpa = db.Column(db.Float)

    passing_year = db.Column(db.Integer)

    skills = db.Column(db.Text)

    experience = db.Column(db.Text)

    resume = db.Column(db.String(255))

    applications = db.relationship(
        "Application",
        backref="student",
        lazy=True,
        cascade="all, delete"
    )

    placements = db.relationship(
        "Placement",
        backref="student",
        lazy=True,
        cascade="all, delete"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.user.name if self.user else None,
            "email": self.user.email if self.user else None,
            "is_active": self.user.is_active if self.user else None,
            "college": self.college,
            "phone": self.phone,
            "degree": self.degree,
            "branch": self.branch,
            "specialization": self.specialization,
            "cgpa": self.cgpa,
            "passing_year": self.passing_year,
            "skills": self.skills,
            "experience": self.experience,
            "resume": self.resume
        }
