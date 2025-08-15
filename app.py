# app.py — cleaned & production-ready
import os
import uuid
import zipfile
import logging
import secrets
import shutil
import traceback
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify,
    send_file, flash, redirect, url_for
)
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

# --- Your utilities ---
from utils.map_parser import parse_html_map
from utils.image_slicer import slice_image
from utils.uploader import upload_to_cloudinary, get_cloudinary_status

# =========================
# App bootstrap (MUST come first)
# =========================
app = Flask(__name__, static_folder="static", static_url_path="/static")
# session/flash will work both locally and on Railway
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
# behind proxy on Railway
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.INFO)

# Cloudinary status (won't block startup)
try:
    app.logger.warning({"cloudinary_status": get_cloudinary_status()})
except Exception as e:
    app.logger.error(f"uploader status failed: {e}\n{traceback.format_exc()}")

# health & debug routes
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/debug/cloudinary")
def debug_cloudinary():
    """Create a tiny image, try upload_to_cloudinary, return the resulting URL."""
    try:
        from PIL import Image
        tmp_path = "/tmp/diag.png"
        Image.new("RGB", (16, 16), (10, 200, 50)).save(tmp_path, "PNG")
        url = upload_to_cloudinary(tmp_path, public_id="diag_test")
        return {"ok": True, "result_url": url}
    except Exception as e:
        app.logger.error(f"/debug/cloudinary failed: {e}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(e)}), 500

# =========================
# Configuration
# =========================
UPLOAD_FOLDER = "uploads"
SLICES_FOLDER = "slices"
OUTPUT_FOLDER = "output"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

for folder in (UPLOAD_FOLDER, SLICES_FOLDER, OUTPUT_FOLDER):
    os.makedirs(folder, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_session_files(session_id: str) -> None:
    """Clean up temporary files for a session."""
    try:
        for base in (UPLOAD_FOLDER, SLICES_FOLDER):
            session_dir = os.path.join(base, session_id)
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir, ignore_errors=True)
    except Exception as e:
        app.logger.error(f"cleanup error: {e}")

# =========================
# Views
# =========================
@app.route("/")
def index():
    return render_template("index.html")

@app.post("/process")
def process_image():
    """
    1) 接收上傳圖 + HTML map
    2) 依 map 切圖
    3) 上傳每塊到 Cloudinary（或 fallback）
    4) 產生 email HTML + ZIP，提供預覽與下載連結
    """
    session_id = str(uuid.uuid4())
    try:
        if "image" not in request.files:
            flash("未提供圖片檔案", "error")
            return redirect(url_for("index"))

        file = request.files["image"]
        map_html = (request.form.get("map_html") or "").strip()

        if not file or file.filename == "":
            flash("未選擇圖片檔案", "error")
            return redirect(url_for("index"))
        if not map_html:
            flash("未提供 HTML 地圖代碼", "error")
            return redirect(url_for("index"))
        if not allowed_file(file.filename):
            flash("檔案格式不正確，請上傳 PNG、JPG、JPEG 或 GIF 檔案。", "error")
            return redirect(url_for("index"))

        # session dirs
        session_upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
        session_slices_dir = os.path.join(SLICES_FOLDER, session_id)
        os.makedirs(session_upload_dir, exist_ok=True)
        os.makedirs(session_slices_dir, exist_ok=True)

        # save upload
        filename = secure_filename(file.filename or "uploaded_image")
        file_path = os.path.join(session_upload_dir, filename)
        file.save(file_path)

        # parse map
        areas = parse_html_map(map_html)
        if not areas:
            cleanup_session_files(session_id)
            flash("在 HTML 地圖中找不到有效的區域標籤", "error")
            return redirect(url_for("index"))

        # slice & upload
        sliced_images = []
        for i, area in enumerate(areas):
            try:
                slice_path = slice_image(file_path, area["coords"], i, session_slices_dir)
                public_id = f"{session_id}_slice_{i}"
                cloud_url = upload_to_cloudinary(slice_path, public_id)
                sliced_images.append({
                    "url": cloud_url,
                    "href": area.get("href"),
                    "alt": area.get("alt", f"圖片切片 {i+1}"),
                    "title": area.get("title", "")
                })
            except Exception as e:
                app.logger.error(f"slice {i} failed: {e}")
                cleanup_session_files(session_id)
                flash(f"處理圖片切片 {i+1} 時發生錯誤：{str(e)}", "error")
                return redirect(url_for("index"))

        # build HTML
        html_content = generate_responsive_html(sliced_images)

        # save HTML & ZIP
        html_filename = f"email_template_{session_id}.html"
        html_path = os.path.join(OUTPUT_FOLDER, html_filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        zip_filename = f"email_template_{session_id}.zip"
        zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(html_path, arcname="email_template.html")

        # cleanup temp
        cleanup_session_files(session_id)

        return render_template(
            "index.html",
            success=True,
            preview_html=html_content,
            download_url=url_for("download_zip", filename=zip_filename),
            sliced_count=len(sliced_images),
        )
    except Exception as e:
        app.logger.error(f"process_image error: {e}\n{traceback.format_exc()}")
        try:
            cleanup_session_files(session_id)
        except Exception:
            pass
        flash(f"發生錯誤：{str(e)}", "error")
        return redirect(url_for("index"))

@app.get("/download/<path:filename>")
def download_zip(filename):
    """
    穩定的下載端點：直接 send_file；
    若找不到檔案 → 回 404 JSON（或改為 flash + redirect 也可）
    """
    try:
        safe = secure_filename(filename)
        file_path = Path(OUTPUT_FOLDER) / safe
        if not file_path.exists():
            # 如果更想回首頁提示，可換成 flash + redirect
            return jsonify({"ok": False, "error": "file not found"}), 404
        return send_file(
            file_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=file_path.name,
            max_age=0,
        )
    except Exception as e:
        app.logger.error(f"download_zip error: {e}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(e)}), 500

# ============== helpers ==============
def generate_responsive_html(sliced_images: list[dict]) -> str:
    """Generate fully responsive HTML with sliced images for all devices."""
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>Responsive Email Template</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
  background-color: #f5f5f5; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;
}
.email-container { width: 100%; max-width: 600px; margin: 0 auto; background: #fff; box-shadow: 0 2px 10px rgba(0,0,0,.1); }
.image-section { display: block; width: 100%; text-decoration: none; border: 0; outline: none; }
.image-section img { width: 100%; height: auto; display: block; border: 0; outline: none; -ms-interpolation-mode: bicubic; max-width: 100%; }
@media (max-width: 599px) {
  .email-container { width: 100% !important; max-width: 100% !important; margin: 0 !important; box-shadow: none !important; }
  .image-section img { width: 100% !important; height: auto !important; }
}
@media (min-width: 600px) and (max-width: 768px) { .email-container { width: 95% !important; max-width: 600px !important; } }
@media (min-width: 769px) { .email-container { width: 600px !important; max-width: 600px !important; } }
@media (prefers-color-scheme: dark) { body { background-color: #1a1a1a; } .email-container { background-color: #2d2d2d; } }
@media print { .email-container { width: 100% !important; max-width: none !important; box-shadow: none !important; } }
</style>
</head>
<body>
  <div class="email-container">""")
    for i, image in enumerate(sliced_images):
        loading_attr = 'loading="lazy"' if i > 0 else ""
        html_parts.append(f"""
    <a href="{image.get('href')}" class="image-section" target="_blank" rel="noopener noreferrer">
      <img src="{image.get('url')}"
           alt="{image.get('alt', f'圖片切片 {i+1}')}"
           title="{image.get('title','')}"
           {loading_attr}
           style="width:100%;height:auto;display:block;border:0;">
    </a>""")
    html_parts.append("""
  </div>
</body>
</html>""")
    return "\n".join(html_parts)

# ------ error handlers ------
@app.errorhandler(413)
def too_large(e):
    flash("File too large. Please upload a smaller image.", "error")
    return redirect(url_for("index"))

@app.errorhandler(500)
def internal_error(e):
    app.logger.error(f"500: {e}\n{traceback.format_exc()}")
    flash("An internal error occurred. Please try again.", "error")
    return redirect(url_for("index"))
