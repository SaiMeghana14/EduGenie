from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_report(filename, class_summary):
    c = canvas.Canvas(filename, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, "EduGenie - Class Report")
    y = 700
    for line in class_summary.split("\n"):
        c.drawString(100, y, line)
        y -= 20
    c.save()
