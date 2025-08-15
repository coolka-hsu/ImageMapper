import os
import logging
import zipfile
import uuid
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from utils.map_parser import parse_html_map
from utils.image_slicer import slice_image
from utils.uploader import upload_to_cloudinary
import shutil

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# app.py (擺在現有程式架構內)
import os, logging
from flask import Flask, jsonify
from PIL import Image

app = Flask(__name__, static_folder="static", static_url_path="/static")

# 啟動時提示是否走 Cloudinary
if os.getenv("CLOUDINARY_URL"):
    logging.warning("Cloudinary enabled (CLOUDINARY_URL present)")
else:
    logging.warning("CLOUDINARY_URL missing, will fallback to local storage")

# 健康檢查：實際做一張 16x16 小圖，測試上傳流程
@app.get("/debug/cloudinary")
def debug_cloudinary():
    from utils.uploader import save_image
    tmp_path = "/tmp/diag.png"
    img = Image.new("RGB", (16, 16), (123, 200, 50))
    img.save(tmp_path, "PNG")
    url = save_image(tmp_path, public_id_prefix="diag")
    return jsonify({
        "has_cloudinary_url": bool(os.getenv("CLOUDINARY_URL")),
        "upload_dest": os.getenv("UPLOAD_DEST", "auto"),
        "result_url": url
    })


# Configuration
UPLOAD_FOLDER = 'uploads'
SLICES_FOLDER = 'slices'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure directories exist
for folder in [UPLOAD_FOLDER, SLICES_FOLDER, OUTPUT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_session_files(session_id):
    """Clean up temporary files for a session"""
    try:
        session_upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
        session_slices_dir = os.path.join(SLICES_FOLDER, session_id)
        
        if os.path.exists(session_upload_dir):
            shutil.rmtree(session_upload_dir)
        if os.path.exists(session_slices_dir):
            shutil.rmtree(session_slices_dir)
    except Exception as e:
        logging.error(f"Error cleaning up session files: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_image():
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Check if file was uploaded
        if 'image' not in request.files:
            flash('未提供圖片檔案', 'error')
            return redirect(url_for('index'))
        
        file = request.files['image']
        map_html = request.form.get('map_html', '').strip()
        
        if file.filename == '':
            flash('未選擇圖片檔案', 'error')
            return redirect(url_for('index'))
        
        if not map_html:
            flash('未提供 HTML 地圖代碼', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            flash('檔案格式不正確，請上傳 PNG、JPG、JPEG 或 GIF 檔案。', 'error')
            return redirect(url_for('index'))
        
        # Create session directories
        session_upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
        session_slices_dir = os.path.join(SLICES_FOLDER, session_id)
        os.makedirs(session_upload_dir, exist_ok=True)
        os.makedirs(session_slices_dir, exist_ok=True)
        
        # Save uploaded file
        filename = secure_filename(file.filename or 'uploaded_image')
        file_path = os.path.join(session_upload_dir, filename)
        file.save(file_path)
        
        # Parse HTML map
        areas = parse_html_map(map_html)
        if not areas:
            cleanup_session_files(session_id)
            flash('在 HTML 地圖中找不到有效的區域標籤', 'error')
            return redirect(url_for('index'))
        
        # Slice image and upload to Cloudinary
        sliced_images = []
        for i, area in enumerate(areas):
            try:
                # Slice image
                slice_path = slice_image(file_path, area['coords'], i, session_slices_dir)
                
                # Upload to Cloudinary
                cloudinary_url = upload_to_cloudinary(slice_path, f"{session_id}_slice_{i}")
                
                sliced_images.append({
                    'url': cloudinary_url,
                    'href': area['href'],
                    'alt': area.get('alt', f'圖片切片 {i+1}'),
                    'title': area.get('title', '')
                })
                
            except Exception as e:
                logging.error(f"Error processing slice {i}: {e}")
                cleanup_session_files(session_id)
                flash(f'處理圖片切片 {i+1} 時發生錯誤：{str(e)}', 'error')
                return redirect(url_for('index'))
        
        # Generate HTML
        html_content = generate_responsive_html(sliced_images)
        
        # Save HTML file
        html_filename = f"email_template_{session_id}.html"
        html_path = os.path.join(OUTPUT_FOLDER, html_filename)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Create ZIP file
        zip_filename = f"email_template_{session_id}.zip"
        zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(html_path, 'email_template.html')
        
        # Clean up temporary files
        cleanup_session_files(session_id)
        
        # Return success response with preview
        return render_template('index.html', 
                             success=True,
                             preview_html=html_content,
                             download_url=url_for('download_zip', filename=zip_filename),
                             sliced_count=len(sliced_images))
        
    except Exception as e:
        logging.error(f"Error in process_image: {e}")
        try:
            if 'session_id' in locals():
                cleanup_session_files(session_id)
        except:
            pass
        flash(f'發生錯誤：{str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_zip(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            flash('檔案不存在', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
        flash('下載檔案時發生錯誤', 'error')
        return redirect(url_for('index'))

def generate_responsive_html(sliced_images):
    """Generate fully responsive HTML with sliced images for all devices"""
    html_parts = []
    
    html_parts.append('''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Responsive Email Template</title>
    <style>
        /* Reset styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background-color: #f5f5f5;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }
        
        /* Email container - responsive design */
        .email-container {
            width: 100%;
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        /* Image sections - fully responsive */
        .image-section {
            display: block;
            width: 100%;
            text-decoration: none;
            border: none;
            outline: none;
        }
        
        .image-section img {
            width: 100%;
            height: auto;
            display: block;
            border: 0;
            outline: none;
            text-decoration: none;
            -ms-interpolation-mode: bicubic;
            max-width: 100%;
        }
        
        /* Mobile-first responsive breakpoints */
        @media only screen and (max-width: 599px) {
            .email-container {
                width: 100% !important;
                max-width: 100% !important;
                margin: 0 !important;
                box-shadow: none !important;
            }
            
            .image-section img {
                width: 100% !important;
                height: auto !important;
            }
        }
        
        /* Tablet breakpoint */
        @media only screen and (min-width: 600px) and (max-width: 768px) {
            .email-container {
                width: 95% !important;
                max-width: 600px !important;
            }
        }
        
        /* Desktop breakpoint */
        @media only screen and (min-width: 769px) {
            .email-container {
                width: 600px !important;
                max-width: 600px !important;
            }
        }
        
        /* High DPI displays */
        @media only screen and (-webkit-min-device-pixel-ratio: 2),
               only screen and (min-resolution: 192dpi) {
            .image-section img {
                image-rendering: -webkit-optimize-contrast;
                image-rendering: optimize-contrast;
            }
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            body {
                background-color: #1a1a1a;
            }
            .email-container {
                background-color: #2d2d2d;
            }
        }
        
        /* Print styles */
        @media print {
            .email-container {
                width: 100% !important;
                max-width: none !important;
                box-shadow: none !important;
            }
        }
    </style>
</head>
<body>
    <div class="email-container">''')
    
    for i, image in enumerate(sliced_images):
        # Add loading="lazy" for better performance on modern browsers
        loading_attr = 'loading="lazy"' if i > 0 else ''
        html_parts.append(f'''
        <a href="{image['href']}" class="image-section" target="_blank" rel="noopener noreferrer">
            <img src="{image['url']}" 
                 alt="{image['alt']}" 
                 title="{image['title']}"
                 {loading_attr}
                 style="width: 100%; height: auto; display: block; border: 0;">
        </a>''')
    
    html_parts.append('''
    </div>
</body>
</html>''')
    
    return '\n'.join(html_parts)

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Please upload a smaller image.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    flash('An internal error occurred. Please try again.', 'error')
    return redirect(url_for('index'))
