# Email Map Image Slicer

## Overview

This is a Flask web application that automatically slices images based on HTML map coordinates and generates responsive email templates. The application takes an image file and HTML map data containing area coordinates, then slices the image into individual pieces based on those coordinates. Each slice is uploaded to Cloudinary for hosting, and the application generates email-ready HTML templates with the sliced images.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme for responsive UI
- **Client-Side Validation**: JavaScript validation for file uploads (size limits, file types)
- **UI Framework**: Bootstrap 5 with Font Awesome icons for modern, responsive design
- **File Upload Interface**: HTML form with drag-and-drop support for image uploads and textarea for HTML map input

### Backend Architecture
- **Web Framework**: Flask with modular utility functions for core processing
- **Request Handling**: RESTful endpoints for file upload and processing
- **Session Management**: UUID-based session tracking for temporary file management
- **File Processing Pipeline**: 
  - Image upload and validation
  - HTML map parsing to extract coordinates
  - Image slicing based on coordinates
  - Cloud upload of sliced images
  - HTML template generation
- **Error Handling**: Comprehensive logging and user-friendly error messages
- **Security**: Werkzeug secure filename handling and file type validation

### Data Processing Components
- **HTML Map Parser**: BeautifulSoup-based parser to extract area coordinates and metadata from HTML map tags
- **Image Slicer**: PIL (Pillow) based image processing to crop images based on parsed coordinates
- **File Management**: Temporary file system with automatic cleanup after processing

### Image Processing Workflow
1. Image upload with validation (file type, size limits)
2. HTML map parsing to extract rectangular coordinates
3. Image slicing using PIL based on extracted coordinates
4. Individual slice upload to Cloudinary
5. HTML template generation with Cloudinary URLs
6. Downloadable ZIP package creation

## External Dependencies

### Cloud Storage
- **Cloudinary**: Primary image hosting service for sliced images
  - Handles image optimization and delivery
  - Provides secure URLs for email template integration
  - Requires CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables

### Python Libraries
- **Flask**: Web framework for application routing and templating
- **Pillow (PIL)**: Image processing library for slicing operations
- **BeautifulSoup4**: HTML parsing for extracting map coordinates
- **Werkzeug**: WSGI utilities for secure file handling
- **CloudinaryPy**: Official Cloudinary Python SDK for image uploads

### Frontend Dependencies
- **Bootstrap 5**: CSS framework loaded from CDN for responsive design
- **Font Awesome**: Icon library for UI enhancement
- **Bootstrap JavaScript**: For interactive components and modals

### Development Environment
- **Python 3.x**: Runtime environment
- **File System**: Local temporary storage for processing (uploads/, slices/, output/ directories)
- **Environment Variables**: Configuration management for sensitive credentials