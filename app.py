from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import os

app = Flask(__name__)

# ── CORS - Most permissive configuration ────────────────────────────────
CORS(app)

@app.after_request
def add_cors_headers(response):
    # Allow any origin
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Max-Age"] = "3600"
    
    # Log CORS headers for debugging
    print(f"CORS Response Headers: {dict(response.headers)}")
    
    return response

# Logo configuration
LOGO_PATH = os.getenv("LOGO_PATH", "eedrlogo.png")

# ── Background Gradient ─────────────────────────────────────────────────
def draw_vertical_gradient(c, width, height):
    steps = 120
    start = colors.Color(0.945, 0.98, 0.945)
    end   = colors.Color(0.90, 1.00, 0.90)
    
    for i in range(steps):
        ratio = i / steps
        r = start.red + (end.red - start.red) * ratio
        g = start.green + (end.green - start.green) * ratio
        b = start.blue + (end.blue - start.blue) * ratio
        c.setFillColor(colors.Color(r, g, b))
        c.rect(0, height * ratio, width, height / steps, stroke=0, fill=1)

# ── Card Component ──────────────────────────────────────────────────────
def draw_card(c, x, y, w, h, title):
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.05))
    c.roundRect(x + 3, y - 3, w, h, 10, stroke=0, fill=1)
    
    c.setFillColor(colors.white)
    c.roundRect(x, y, w, h, 10, stroke=0, fill=1)
    
    c.setFillColor(colors.Color(0.22, 0.68, 0.42))
    c.rect(x, y + h - 8, w, 8, stroke=0, fill=1)
    
    c.setFillColor(colors.darkgreen)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(x + 20, y + h - 26, title)

# ── Core PDF Generator ──────────────────────────────────────────────────
def generate_pdf(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    draw_vertical_gradient(c, width, height)

    # Logo
    try:
        logo_w = 2.1 * inch
        logo_h = logo_w * 0.48
        c.drawImage(
            LOGO_PATH,
            x = (width - logo_w) / 2,
            y = height - logo_h - 0.45 * inch,
            width = logo_w,
            height = logo_h,
            mask='auto'
        )
    except Exception as e:
        print(f"Logo error: {str(e)}")
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.grey)
        c.drawString(
            (width - 180) / 2,
            height - 1.1 * inch,
            "[EEdR Logo unavailable]"
        )

    y_pos = height - 2.6 * inch
    card_x = 0.75 * inch
    card_width = width - 1.5 * inch

    # Bundle Card
    card_height = 195
    draw_card(c, card_x, y_pos - card_height, card_width, card_height, "Bundle")
    
    y_inner = y_pos - 52
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

    # Credibility Card
    card_height = 160
    draw_card(c, card_x, y_pos - card_height, card_width, card_height, "Credibility")
    
    y_inner = y_pos - 52
    points = data.get("credibility_points", [])
    if not points:
        points = ["No credibility points available"]
    
    for point in points[:5]:
        c.setFont("Helvetica", 11)
        c.drawString(card_x + 32, y_inner, f"• {point}")
        y_inner -= 20

    y_pos -= card_height + 24

    # Operations Card
    card_height = 185
    draw_card(c, card_x, y_pos - card_height, card_width, card_height, "Operations")
    
    y_inner = y_pos - 52
    ops_items = [
        ("Recommendations Followed", data.get("ops_recommendations", "—")),
        ("Energy Saved",             data.get("ops_energy_saved", "—")),
        ("Resources Saved",          data.get("ops_resources_saved", "—")),
        ("Maintenance Downtime",     data.get("ops_downtime", "—")),
        ("Data Drift Accuracy",      "99%"),
    ]
    
    for label, value in ops_items:
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(card_x + 24, y_inner, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(card_x + 260, y_inner, str(value))
        y_inner -= 22

    # Footer
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.darkgreen)
    c.drawString(0.75 * inch, 0.45 * inch, "Provided by Climate Care Consulting")

    c.save()
    buffer.seek(0)
    return buffer

# ── API Endpoint ────────────────────────────────────────────────────────
@app.route("/export-pdf", methods=["POST", "OPTIONS"])
def export_pdf():
    print(f"\n{'='*60}")
    print(f"Request Method: {request.method}")
    print(f"Request Origin: {request.headers.get('Origin', 'No origin header')}")
    print(f"Request Headers: {dict(request.headers)}")
    print(f"{'='*60}\n")
    
    if request.method == "OPTIONS":
        print("Handling OPTIONS preflight request")
        response = make_response("", 204)
        return response

    if not request.is_json:
        print(f"ERROR: Request is not JSON. Content-Type: {request.content_type}")
        return jsonify({"error": "JSON body required"}), 400

    try:
        request_data = request.get_json()
        print(f"Received data: {request_data}")
        
        pdf_buffer = generate_pdf(request_data)
        
        response = make_response(pdf_buffer.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = 'attachment; filename="Energy_Report.pdf"'
        
        print(f"✅ PDF generated successfully! Size: {len(pdf_buffer.getvalue())} bytes")
        
        return response
        
    except Exception as e:
        print(f"❌ PDF generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to generate PDF", "detail": str(e)}), 500

# Health check endpoint
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy", 
        "service": "PDF Export Service",
        "endpoints": {
            "/": "Health check",
            "/export-pdf": "POST - Generate PDF from JSON data"
        }
    })

# ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀 Starting PDF Export Service on port {port}")
    print(f"📍 Endpoints available:")
    print(f"   GET  / - Health check")
    print(f"   POST /export-pdf - Generate PDF\n")
    app.run(host="0.0.0.0", port=port, debug=False)
