from extensions import db


class ReminderSettings(db.Model):
    __tablename__ = "reminder_settings"

    id = db.Column(db.Integer, primary_key=True)

    deadline_reminder_hour = db.Column(db.Integer, nullable=False, default=9)
    deadline_reminder_minute = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "deadline_reminder_hour": self.deadline_reminder_hour,
            "deadline_reminder_minute": self.deadline_reminder_minute,
        }

    @classmethod
    def get_singleton(cls):
        settings = cls.query.get(1)
        if not settings:
            settings = cls(id=1)
            db.session.add(settings)
            db.session.commit()
        return settings
