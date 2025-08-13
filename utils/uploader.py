import os
import logging
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.exceptions import Error as CloudinaryError

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

def upload_to_cloudinary(image_path, public_id=None):
    """
    Upload an image to Cloudinary
    
    Args:
        image_path (str): Path to the image file
        public_id (str): Optional public ID for the uploaded image
        
    Returns:
        str: Cloudinary URL of the uploaded image
    """
    try:
        # Check if Cloudinary is configured
        if not all([
            os.environ.get("CLOUDINARY_CLOUD_NAME"),
            os.environ.get("CLOUDINARY_API_KEY"),
            os.environ.get("CLOUDINARY_API_SECRET")
        ]):
            raise Exception("Cloudinary credentials not properly configured. Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables.")
        
        # Upload options
        upload_options = {
            'resource_type': 'image',
            'format': 'auto',
            'quality': 'auto:good',
            'fetch_format': 'auto'
        }
        
        if public_id:
            upload_options['public_id'] = public_id
            upload_options['overwrite'] = True
        
        # Upload the image
        result = cloudinary.uploader.upload(image_path, **upload_options)
        
        # Get the secure URL
        image_url = result.get('secure_url')
        
        if not image_url:
            raise Exception("Failed to get image URL from Cloudinary response")
        
        logging.info(f"Successfully uploaded image to Cloudinary: {image_url}")
        return image_url
        
    except CloudinaryError as e:
        logging.error(f"Cloudinary error: {e}")
        raise Exception(f"Cloudinary upload failed: {str(e)}")
    except Exception as e:
        logging.error(f"Error uploading to Cloudinary: {e}")
        raise Exception(f"Failed to upload image: {str(e)}")

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
