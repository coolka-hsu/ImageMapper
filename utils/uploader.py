import os
import logging
import shutil
from urllib.parse import urljoin
from flask import request

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    from cloudinary.exceptions import Error as CloudinaryError
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False
    logging.warning("Cloudinary not available, using local storage")

def upload_to_cloudinary(image_path, public_id=None):
    """
    Upload an image to Cloudinary or use local storage as fallback
    
    Args:
        image_path (str): Path to the image file
        public_id (str): Optional public ID for the uploaded image
        
    Returns:
        str: Image URL (Cloudinary or local)
    """
    # First try local storage method for reliability
    try:
        return upload_to_local_storage(image_path, public_id)
    except Exception as local_error:
        logging.error(f"Local storage failed: {local_error}")
    
    # Fallback to Cloudinary if available and configured
    if not CLOUDINARY_AVAILABLE:
        raise Exception("Neither local storage nor Cloudinary is available")
    
    try:
        # Check if Cloudinary is configured
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
        api_key = os.environ.get("CLOUDINARY_API_KEY") 
        api_secret = os.environ.get("CLOUDINARY_API_SECRET")
        
        if not all([cloud_name, api_key, api_secret]):
            raise Exception("Cloudinary credentials not configured")
        
        # Try very simple upload without extra parameters
        result = cloudinary.uploader.upload(
            image_path,
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        
        image_url = result.get('secure_url')
        if not image_url:
            raise Exception("No URL in Cloudinary response")
        
        logging.info(f"Successfully uploaded to Cloudinary: {image_url}")
        return image_url
        
    except Exception as e:
        logging.error(f"Cloudinary upload failed: {e}")
        raise Exception(f"Both local and Cloudinary upload failed: {str(e)}")

def upload_to_local_storage(image_path, public_id=None):
    """
    Store image locally and return a URL
    
    Args:
        image_path (str): Path to the image file
        public_id (str): Optional public ID for the uploaded image
        
    Returns:
        str: Local URL to the image
    """
    try:
        # Create static images directory
        static_images_dir = os.path.join('static', 'images')
        os.makedirs(static_images_dir, exist_ok=True)
        
        # Generate filename
        if public_id:
            filename = f"{public_id}.png"
        else:
            import uuid
            filename = f"{uuid.uuid4()}.png"
        
        # Copy image to static directory
        destination_path = os.path.join(static_images_dir, filename)
        shutil.copy2(image_path, destination_path)
        
        # Generate URL (assuming we're running on Replit)
        base_url = os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')
        if not base_url.startswith('http'):
            base_url = f"https://{base_url}"
        
        image_url = f"{base_url}/static/images/{filename}"
        
        logging.info(f"Successfully stored locally: {image_url}")
        return image_url
        
    except Exception as e:
        logging.error(f"Local storage error: {e}")
        raise Exception(f"Failed to store image locally: {str(e)}")

def delete_from_cloudinary(public_id):
    """
    Delete an image from Cloudinary
    
    Args:
        public_id (str): Public ID of the image to delete
        
    Returns:
        bool: True if successfully deleted
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        logging.error(f"Error deleting from Cloudinary: {e}")
        return False

def get_cloudinary_status():
    """
    Check if Cloudinary is properly configured
    
    Returns:
        dict: Status information
    """
    try:
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
        api_key = os.environ.get("CLOUDINARY_API_KEY")
        api_secret = os.environ.get("CLOUDINARY_API_SECRET")
        
        if not all([cloud_name, api_key, api_secret]):
            return {
                'configured': False,
                'message': 'Missing Cloudinary credentials'
            }
        
        # Test API connection
        cloudinary.api.ping()
        
        return {
            'configured': True,
            'cloud_name': cloud_name,
            'message': 'Cloudinary is properly configured'
        }
        
    except Exception as e:
        return {
            'configured': False,
            'message': f'Cloudinary connection failed: {str(e)}'
        }
