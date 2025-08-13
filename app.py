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
            flash('No image file provided', 'error')
            return redirect(url_for('index'))
        
        file = request.files['image']
        map_html = request.form.get('map_html', '').strip()
        
        if file.filename == '':
            flash('No image file selected', 'error')
            return redirect(url_for('index'))
        
        if not map_html:
            flash('No HTML map provided', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload PNG, JPG, JPEG, or GIF files.', 'error')
            return redirect(url_for('index'))
        
        # Create session directories
        session_upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
        session_slices_dir = os.path.join(SLICES_FOLDER, session_id)
        os.makedirs(session_upload_dir, exist_ok=True)
        os.makedirs(session_slices_dir, exist_ok=True)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(session_upload_dir, filename)
        file.save(file_path)
        
        # Parse HTML map
        areas = parse_html_map(map_html)
        if not areas:
            cleanup_session_files(session_id)
            flash('No valid area tags found in HTML map', 'error')
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
                    'alt': area.get('alt', f'Image slice {i+1}'),
                    'title': area.get('title', '')
                })
                
            except Exception as e:
                logging.error(f"Error processing slice {i}: {e}")
                cleanup_session_files(session_id)
                flash(f'Error processing image slice {i+1}: {str(e)}', 'error')
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
        if 'session_id' in locals():
            cleanup_session_files(session_id)
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_zip(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            flash('File not found', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
        flash('Error downloading file', 'error')
        return redirect(url_for('index'))

def generate_responsive_html(sliced_images):
    """Generate responsive HTML with sliced images"""
    html_parts = []
    
    html_parts.append('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Template</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }
        .email-container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
        }
        .image-section {
            display: block;
            width: 100%;
        }
        .image-section img {
            width: 100%;
            height: auto;
            display: block;
            border: 0;
            outline: none;
            text-decoration: none;
        }
        @media only screen and (max-width: 600px) {
            .email-container {
                width: 100% !important;
            }
        }
    </style>
</head>
<body>
    <div class="email-container">''')
    
    for image in sliced_images:
        html_parts.append(f'''
        <a href="{image['href']}" class="image-section" target="_blank">
            <img src="{image['url']}" alt="{image['alt']}" title="{image['title']}">
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
