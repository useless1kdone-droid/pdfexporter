from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import os

app = Flask(__name__)

# ── CORS ────────────────────────────────────────────────────────────────
# Most reliable setup for Render + Vercel + local dev
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",
            "http://localhost:5173",       # Vite default
            "https://eedr-iot.vercel.app",
            "https://*.vercel.app",        # preview branches
            "*"                            # temporary fallback - remove later
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Optional: explicit OPTIONS handler (very helpful on Render)
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

# Logo configuration
LOGO_PATH = os.getenv("LOGO_PATH", "eedrlogo.png")  # must be in repo root

# ── Background Gradient ─────────────────────────────────────────────────
def draw_vertical_gradient(c, width, height):
    steps = 120
    start = colors.Color(0.945, 0.98, 0.945)   # very light mint
    end   = colors.Color(0.90, 1.00, 0.90)     # soft lime tint
    
    for i in range(steps):
        ratio = i / steps
        r = start.red + (end.red - start.red) * ratio
        g = start.green + (end.green - start.green) * ratio
        b = start.blue + (end.blue - start.blue) * ratio
        c.setFillColor(colors.Color(r, g, b))
        c.rect(0, height * ratio, width, height / steps, stroke=0, fill=1)

# ── Card Component ──────────────────────────────────────────────────────
def draw_card(c, x, y, w, h, title):
    # Soft shadow
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.05))
    c.roundRect(x + 3, y - 3, w, h, 10, stroke=0, fill=1)
    
    # White card
    c.setFillColor(colors.white)
    c.roundRect(x, y, w, h, 10, stroke=0, fill=1)
    
    # Top accent bar
    c.setFillColor(colors.Color(0.22, 0.68, 0.42))  # nice green
    c.rect(x, y + h - 8, w, 8, stroke=0, fill=1)
    
    # Title
    c.setFillColor(colors.darkgreen)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(x + 20, y + h - 26, title)

# ── Core PDF Generator ──────────────────────────────────────────────────
def generate_pdf(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4   # ~595 x 842 pt

    # Background
    draw_vertical_gradient(c, width, height)

    # ── Logo ────────────────────────────────────────────────────────────
    try:
        logo_w = 2.1 * inch
        logo_h = logo_w * 0.48   # adjust ratio based on your logo
        c.drawImage(
            LOGO_PATH,
            x = (width - logo_w) / 2,
            y = height - logo_h - 0.45 * inch,
            width = logo_w,
            height = logo_h,
            mask='auto'
        )
    except Exception as e:
        print(f"Logo error: {str(e)}")  # will show in Render logs
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.grey)
        c.drawString(
            (width - 180) / 2,
            height - 1.1 * inch,
            "[EEdR Logo unavailable]"
        )

    # Starting Y position under logo
    y_pos = height - 2.6 * inch
    card_x = 0.75 * inch
    card_width = width - 1.5 * inch

    # ── 1. Bundle Card ──────────────────────────────────────────────────
    card_height = 195
    draw_card(c, card_x, y_pos - card_height, card_width, card_height, "Bundle")
    
    y_inner = y_pos - 52
    c.setFont("Helvetica", 11)
    
    bundle_items = [
        ("Building",        data.get("bundle_building", "—")),
        ("Meter",           data.get("bundle_meter", "—")),
        ("Realtime Data",   data.get("bundle_realtime", "—")),
        ("Baseline Data",   data.get("bundle_baseline", "—")),
        ("Delta (Live)",    data.get("bundle_delta", "—")),
    ]
    
    for label, value in bundle_items:
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(card_x + 24, y_inner, f"{label}:")
        
        c.setFont("Helvetica", 11)
        c.drawString(card_x + 170, y_inner, str(value))
        y_inner -= 22

    y_pos -= card_height + 24

    # ── 2. Credibility Card ─────────────────────────────────────────────
    card_height = 160
    draw_card(c, card_x, y_pos - card_height, card_width, card_height, "Credibility")
    
    y_inner = y_pos - 52
    points = data.get("credibility_points", [])
    
    if not points:
        points = ["No credibility points available"]
    
    for point in points[:5]:  # limit to avoid overflow
        c.setFont("Helvetica", 11)
        c.drawString(card_x + 32, y_inner, f"• {point}")
        y_inner -= 20

    y_pos -= card_height + 24

    # ── 3. Operations Card ──────────────────────────────────────────────
    card_height = 185
    draw_card(c, card_x, y_pos - card_height, card_width, card_height, "Operations")
    
    y_inner = y_pos - 52
    ops_items = [
        ("Recommendations Followed", data.get("ops_recommendations", "—")),
        ("Energy Saved",             data.get("ops_energy_saved", "—")),
        ("Resources Saved",          data.get("ops_resources_saved", "—")),
        ("Maintenance Downtime",     data.get("ops_downtime", "—")),
        ("Data Drift Accuracy",      "99%"),   # hardcoded as per your request
    ]
    
    for label, value in ops_items:
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(card_x + 24, y_inner, f"{label}:")
        
        c.setFont("Helvetica", 11)
        c.drawString(card_x + 260, y_inner, str(value))
        y_inner -= 22

    # ── Footer ──────────────────────────────────────────────────────────
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.darkgreen)
    c.drawString(
        0.75 * inch,
        0.45 * inch,
        "Provided by Climate Care Consulting"
    )

    c.save()
    buffer.seek(0)
    return buffer

# ── API Endpoint ────────────────────────────────────────────────────────
@app.route("/export-pdf", methods=["POST", "OPTIONS"])
def export_pdf():
    if request.method == "OPTIONS":
        return "", 204

    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400

    try:
        pdf_buffer = generate_pdf(request.get_json())
        response = make_response(pdf_buffer.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = 'attachment; filename="Energy_Report.pdf"'
        return response
    except Exception as e:
        print(f"PDF generation error: {str(e)}")
        return jsonify({"error": "Failed to generate PDF", "detail": str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
