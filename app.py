from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import os

# ─────────────────────────────────────────────────────────────
# Flask app
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)

# Enable CORS for localhost (dev) and deployed frontend
FRONTEND_DOMAINS = [
    "http://localhost:3000",  # local development
    "https://myfrontend.onrender.com",  # replace with your actual frontend
]
CORS(app, resources={r"/export-pdf": {"origins": FRONTEND_DOMAINS}})

LOGO_PATH = os.getenv("LOGO_PATH", "eedrlogo.png")


# ─────────────────────────────────────────────────────────────
# Draw vertical gradient background
# ─────────────────────────────────────────────────────────────
def draw_vertical_gradient(c, width, height):
    steps = 140
    start = colors.Color(0.94, 0.98, 0.94)  # very light green
    end   = colors.Color(0.88, 1.00, 0.88)  # lime tint

    for i in range(steps):
        r = start.red   + (end.red   - start.red)   * (i / steps)
        g = start.green + (end.green - start.green) * (i / steps)
        b = start.blue  + (end.blue  - start.blue)  * (i / steps)

        c.setFillColor(colors.Color(r, g, b))
        c.rect(0, height * i / steps, width, height / steps, stroke=0, fill=1)


# ─────────────────────────────────────────────────────────────
# Draw a card
# ─────────────────────────────────────────────────────────────
def draw_card(c, x, y, w, h, title):
    # Shadow
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.06))
    c.roundRect(x + 4, y - 4, w, h, 12, stroke=0, fill=1)

    # Card body
    c.setFillColor(colors.white)
    c.roundRect(x, y, w, h, 12, stroke=0, fill=1)

    # Accent bar
    c.setFillColor(colors.Color(0.25, 0.7, 0.45))
    c.rect(x, y + h - 10, w, 10, stroke=0, fill=1)

    # Title
    c.setFillColor(colors.darkgreen)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 18, y + h - 28, title)


# ─────────────────────────────────────────────────────────────
# Generate PDF
# ─────────────────────────────────────────────────────────────
def generate_pdf(data, logo_path=LOGO_PATH):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Background
    draw_vertical_gradient(c, width, height)

    # Logo
    try:
        logo_width = 2 * inch
        logo_height = logo_width * 0.5
        c.drawImage(
            logo_path,
            (width - logo_width) / 2,
            height - logo_height - 0.5 * inch,
            logo_width,
            logo_height,
            mask='auto'
        )
    except Exception:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1 * inch, height - 1.2 * inch, "[Logo unavailable]")

    y = height - 2.5 * inch
    card_x = 0.8 * inch
    card_w = width - 1.6 * inch

    # ── Bundle Card ───────────────────────────
    card_h = 180
    draw_card(c, card_x, y - card_h, card_w, card_h, "Bundle")

    y_inner = y - 55
    c.setFont("Helvetica", 11)
    bundle_fields = [
        ("Building", data.get("bundle_building", "N/A")),
        ("Meter", data.get("bundle_meter", "N/A")),
        ("Realtime Data", data.get("bundle_realtime", "N/A")),
        ("Baseline Data", data.get("bundle_baseline", "N/A")),
        ("Delta (Live)", data.get("bundle_delta", "N/A")),
    ]

    for label, value in bundle_fields:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(card_x + 24, y_inner, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(card_x + 180, y_inner, str(value))
        y_inner -= 20

    y -= card_h + 28

    # ── Credibility Card ─────────────────────
    card_h = 150
    draw_card(c, card_x, y - card_h, card_w, card_h, "Credibility")

    y_inner = y - 55
    points = data.get("credibility_points", []) or ["No credibility points available"]

    c.setFont("Helvetica", 11)
    for p in points:
        c.drawString(card_x + 36, y_inner, f"• {p}")
        y_inner -= 18

    y -= card_h + 28

    # ── Operations Card ──────────────────────
    card_h = 170
    draw_card(c, card_x, y - card_h, card_w, card_h, "Operations")

    y_inner = y - 55
    ops_fields = [
        ("Recommendations Followed", data.get("ops_recommendations", "N/A")),
        ("Energy Saved", data.get("ops_energy_saved", "N/A")),
        ("Resources Saved", data.get("ops_resources_saved", "N/A")),
        ("Maintenance Downtime", data.get("ops_downtime", "N/A")),
        ("Data Drift Accuracy", "99%"),
    ]

    for label, value in ops_fields:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(card_x + 24, y_inner, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(card_x + 260, y_inner, str(value))
        y_inner -= 18

    # Footer
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.darkgreen)
    c.drawString(
        1 * inch,
        0.5 * inch,
        "Provided by Climate Care Consulting"
    )

    c.save()
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────────────────────
# API Route
# ─────────────────────────────────────────────────────────────
@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    try:
        pdf = generate_pdf(request.get_json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    response = make_response(pdf.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=energy_report.pdf"
    return response


# ─────────────────────────────────────────────────────────────
# Local development only
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
