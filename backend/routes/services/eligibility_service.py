from datetime import date

from utils.validators import validate_cgpa


def split_values(value):
    if not value:
        return set()
    return {
        item.strip().lower()
        for item in str(value).replace(";", ",").split(",")
        if item.strip()
    }


def student_matches_job(student, job):
    reasons = []

    if not validate_cgpa(student.cgpa, job.minimum_cgpa):
        reasons.append(f"Minimum CGPA required is {job.minimum_cgpa}")

    if job.eligibility_branch:
        allowed_branches = split_values(job.eligibility_branch)
        student_branch = (student.branch or student.specialization or "").strip().lower()
        if allowed_branches and student_branch not in allowed_branches:
            reasons.append("Student branch is not eligible for this drive")

    if job.eligibility_year and student.passing_year != job.eligibility_year:
        reasons.append(f"Passing year must be {job.eligibility_year}")

    required_skills = split_values(job.skills_required)
    student_skills = split_values(student.skills)
    missing_skills = sorted(required_skills - student_skills)
    if missing_skills:
        reasons.append("Missing skills: " + ", ".join(missing_skills))

    if job.last_date and job.last_date < date.today():
        reasons.append("Application deadline has passed")

    if not job.approved or job.status not in {"Approved", "Active"}:
        reasons.append("Drive is not open for applications")

    return len(reasons) == 0, reasons
