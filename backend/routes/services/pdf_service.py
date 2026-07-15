import os
from datetime import datetime, timezone

from flask import current_app
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_monthly_report_pdf(stats):
    export_dir = os.path.join(current_app.instance_path, "reports")
    os.makedirs(export_dir, exist_ok=True)
    filename = f"monthly_report_{datetime.now(timezone.utc).strftime('%Y_%m')}.pdf"
    path = os.path.join(export_dir, filename)

    pdf = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 72

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, y, "Placement Portal Monthly Report")
    y -= 36

    pdf.setFont("Helvetica", 11)
    for label, value in stats.items():
        pdf.drawString(72, y, f"{label.replace('_', ' ').title()}: {value}")
        y -= 20

    pdf.save()
    return filename, path
