from PIL import Image
import os
import logging

def slice_image(image_path, coords, slice_index, output_dir):
    """
    Slice an image based on coordinates
    
    Args:
        image_path (str): Path to the source image
        coords (list): [x1, y1, x2, y2] coordinates for slicing
        slice_index (int): Index for naming the output file
        output_dir (str): Directory to save sliced images
        
    Returns:
        str: Path to the sliced image file
    """
    try:
        # Open the image
        with Image.open(image_path) as img:
            # Get image dimensions
            img_width, img_height = img.size
            
            # Extract coordinates
            x1, y1, x2, y2 = coords
            
            # Validate coordinates
            if x1 < 0 or y1 < 0 or x2 > img_width or y2 > img_height:
                raise ValueError(f"Coordinates {coords} are outside image bounds ({img_width}x{img_height})")
            
            if x1 >= x2 or y1 >= y2:
                raise ValueError(f"Invalid coordinates: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
            
            # Crop the image
            cropped_img = img.crop((x1, y1, x2, y2))
            
            # Generate output filename
            output_filename = f"slice_{slice_index}.png"
            output_path = os.path.join(output_dir, output_filename)
            
            # Save the cropped image as PNG to maintain quality
            cropped_img.save(output_path, 'PNG', optimize=True)
            
            logging.info(f"Successfully sliced image: {output_path}")
            return output_path
            
    except Exception as e:
        logging.error(f"Error slicing image: {e}")
        raise Exception(f"Failed to slice image: {str(e)}")

def get_image_dimensions(image_path):
    """
    Get dimensions of an image
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        tuple: (width, height)
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logging.error(f"Error getting image dimensions: {e}")
        raise Exception(f"Failed to get image dimensions: {str(e)}")

def validate_image_file(image_path):
    """
    Validate that the file is a valid image
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        bool: True if valid image
    """
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception as e:
        logging.error(f"Invalid image file: {e}")
        return False
