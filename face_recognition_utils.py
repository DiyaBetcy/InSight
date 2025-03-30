import logging
import numpy as np
import face_recognition
import cv2
from PIL import Image

def detect_faces_from_image(image_file):
    """
    Detect faces in an image and return face encodings.
    
    Args:
        image_file: A file-like object containing image data
    
    Returns:
        A list of face encodings found in the image
    """
    try:
        # Open the image with PIL
        image = Image.open(image_file)
        
        # Convert PIL image to numpy array (RGB)
        image_np = np.array(image)
        
        # Convert to BGR (OpenCV format) if needed
        if len(image_np.shape) == 3 and image_np.shape[2] == 3:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        # Get face locations
        face_locations = face_recognition.face_locations(image_np, model="hog")
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(image_np, face_locations)
        
        logging.debug(f"Detected {len(face_encodings)} faces in image")
        
        return face_encodings
    except Exception as e:
        logging.error(f"Error detecting faces: {str(e)}")
        raise

def compare_faces(known_encoding, unknown_encoding, tolerance=0.6):
    """
    Compare a known face encoding with an unknown face encoding.
    
    Args:
        known_encoding: The face encoding of a known person
        unknown_encoding: The face encoding to compare against
        tolerance: The tolerance for face comparison (default: 0.6)
        
    Returns:
        True if faces match, False otherwise
    """
    try:
        # Convert to numpy arrays if needed
        if not isinstance(known_encoding, np.ndarray):
            known_encoding = np.array(known_encoding)
        
        if not isinstance(unknown_encoding, np.ndarray):
            unknown_encoding = np.array(unknown_encoding)
        
        # Reshape if needed
        if len(known_encoding.shape) == 1:
            known_encoding = known_encoding.reshape(1, -1)
        
        if len(unknown_encoding.shape) == 1:
            unknown_encoding = unknown_encoding.reshape(1, -1)
        
        # Compare faces
        results = face_recognition.compare_faces(known_encoding, unknown_encoding, tolerance)
        
        # Return True if any match
        return any(results)
    except Exception as e:
        logging.error(f"Error comparing faces: {str(e)}")
        return False
