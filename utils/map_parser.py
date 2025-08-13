import re
from bs4 import BeautifulSoup
import logging

def parse_html_map(html_content):
    """
    Parse HTML map content and extract area coordinates and links
    
    Args:
        html_content (str): HTML content containing map and area tags
        
    Returns:
        list: List of dictionaries containing area information
    """
    try:
        # Clean up the HTML content
        html_content = html_content.strip()
        
        # If it's just area tags without map wrapper, wrap it
        if not html_content.startswith('<map'):
            html_content = f'<map name="temp">{html_content}</map>'
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all area tags
        areas = soup.find_all('area')
        
        parsed_areas = []
        
        for area in areas:
            try:
                # Extract coordinates
                coords_str = area.get('coords', '')
                if not coords_str:
                    logging.warning("Area tag missing coords attribute")
                    continue
                
                # Parse coordinates (assuming rect format: x1,y1,x2,y2)
                coords = [int(x.strip()) for x in coords_str.split(',')]
                
                if len(coords) != 4:
                    logging.warning(f"Invalid coordinates format: {coords_str}")
                    continue
                
                # Extract other attributes
                href = area.get('href', '#')
                alt = area.get('alt', '')
                title = area.get('title', '')
                shape = area.get('shape', 'rect')
                
                # Only support rect shape for now
                if shape.lower() != 'rect':
                    logging.warning(f"Unsupported shape: {shape}. Only 'rect' is supported.")
                    continue
                
                parsed_areas.append({
                    'coords': coords,  # [x1, y1, x2, y2]
                    'href': href,
                    'alt': alt,
                    'title': title,
                    'shape': shape
                })
                
            except ValueError as e:
                logging.error(f"Error parsing coordinates: {e}")
                continue
            except Exception as e:
                logging.error(f"Error parsing area tag: {e}")
                continue
        
        logging.info(f"Successfully parsed {len(parsed_areas)} area tags")
        return parsed_areas
        
    except Exception as e:
        logging.error(f"Error parsing HTML map: {e}")
        return []

def validate_coordinates(coords, image_width, image_height):
    """
    Validate that coordinates are within image bounds
    
    Args:
        coords (list): [x1, y1, x2, y2]
        image_width (int): Image width
        image_height (int): Image height
        
    Returns:
        bool: True if coordinates are valid
    """
    try:
        x1, y1, x2, y2 = coords
        
        # Check if coordinates are within bounds
        if (x1 >= 0 and y1 >= 0 and 
            x2 <= image_width and y2 <= image_height and
            x1 < x2 and y1 < y2):
            return True
        
        return False
        
    except Exception:
        return False
