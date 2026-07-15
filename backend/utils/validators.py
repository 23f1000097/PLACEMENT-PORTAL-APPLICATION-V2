import re
from datetime import datetime

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def allowed_file(filename, allowed_extensions):

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in allowed_extensions


def validate_cgpa(student_cgpa, required_cgpa):

    if required_cgpa is None:
        return True
    if student_cgpa is None:
        return False
    return float(student_cgpa) >= float(required_cgpa)


def validate_email(email):

    return isinstance(email, str) and bool(EMAIL_RE.match(email.strip()))


def validate_positive_number(value, allow_zero=True, field_name="value"):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be a number"
    if allow_zero and number < 0:
        return None, f"{field_name} must be zero or greater"
    if not allow_zero and number <= 0:
        return None, f"{field_name} must be greater than zero"
    return number, None


def validate_year(value, field_name="year", min_year=1950, max_year=2100):
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be a whole number"
    if year < min_year or year > max_year:
        return None, f"{field_name} must be between {min_year} and {max_year}"
    return year, None


def validate_password(password):

    return isinstance(password, str) and len(password) >= 6


def parse_bool(value, default=None):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return default


def parse_date(value):
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_datetime(value):
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value
    return datetime.fromisoformat(value)


def require_fields(payload, fields):
    missing = [field for field in fields if not payload.get(field)]
    return missing
