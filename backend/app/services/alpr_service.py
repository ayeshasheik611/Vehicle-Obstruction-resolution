"""
ALPR (Automatic License Plate Recognition) service

This module provides image preprocessing and license plate recognition
using OpenALPR library.

**Validates Requirements**: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 4.13, 4.14, 4.15, 17.1, 17.2, 17.3, 17.4, 17.5
"""
import os
import base64
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any
import cv2
import numpy as np
from PIL import Image
import io

from app.utils.vehicle_validation import validate_vehicle_format, normalize_vehicle_number


class ALPRService:
    """Service for Automatic License Plate Recognition"""
    
    def __init__(self):
        """Initialize ALPR service"""
        self.max_image_size = (1920, 1080)  # Requirement 4.3
        self.contrast_factor = 1.5  # Requirement 4.5
        
    def preprocess_image(self, image_data: bytes) -> Optional[np.ndarray]:
        """
        Preprocess image for better ALPR accuracy
        
        Steps:
        1. Resize if larger than 1920x1080 (Requirement 4.3)
        2. Convert to grayscale (Requirement 4.4)
        3. Enhance contrast by 1.5x (Requirement 4.5)
        4. Apply Gaussian blur for noise reduction (Requirement 4.5)
        5. Apply sharpen filter (Requirement 4.6)
        
        **Validates Requirements**: 4.2, 4.3, 4.4, 4.5, 4.6
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Preprocessed image as numpy array, or None if processing fails
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                print("Failed to decode image")
                return None
            
            # Step 1: Resize if larger than max size (Requirement 4.3)
            height, width = img.shape[:2]
            max_width, max_height = self.max_image_size
            
            if width > max_width or height > max_height:
                # Calculate scaling factor to maintain aspect ratio
                scale = min(max_width / width, max_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                print(f"Resized image from {width}x{height} to {new_width}x{new_height}")
            
            # Step 2: Convert to grayscale (Requirement 4.4)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Step 3: Enhance contrast (Requirement 4.5)
            enhanced = cv2.convertScaleAbs(gray, alpha=self.contrast_factor, beta=0)
            
            # Step 4: Apply Gaussian blur for noise reduction (Requirement 4.5)
            blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
            
            # Step 5: Apply sharpen filter (Requirement 4.6)
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]])
            sharpened = cv2.filter2D(blurred, -1, kernel)
            
            return sharpened
            
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return None
    
    def extract_plate_number(self, image_data: bytes) -> Dict[str, Any]:
        """
        Extract license plate number from image using ALPR
        
        Process:
        1. Try Plate Recognizer API first (95%+ accuracy)
        2. Fallback to EasyOCR if API fails
        3. Preprocess image
        4. Detect license plate regions
        5. Perform OCR to extract text
        6. Normalize extracted text
        7. Validate format
        8. Delete image immediately
        
        **Validates Requirements**: 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 4.13, 4.14, 4.15, 17.1, 17.2, 17.3, 17.4, 17.5
        
        Args:
            image_data: Base64 encoded image data
            
        Returns:
            Dictionary with:
                - success: bool
                - vehicle_number: str (normalized, if found)
                - confidence: float (0-1)
                - message: str
        """
        temp_file_path = None
        
        try:
            # Decode base64 image
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": f"Invalid image data: {str(e)}"
                }
            
            # Try cloud APIs first (best accuracy: 95%+)
            
            # Option 1: Try Plate Recognizer API
            try:
                from app.services.plate_recognizer_service import plate_recognizer_service
                
                print("Trying Plate Recognizer API...")
                api_result = plate_recognizer_service.recognize_plate(image_bytes)
                
                if api_result["success"]:
                    # Normalize and validate
                    normalized = normalize_vehicle_number(api_result["vehicle_number"])
                    
                    if validate_vehicle_format(normalized):
                        print(f"Plate Recognizer success: {normalized}")
                        return {
                            "success": True,
                            "vehicle_number": normalized,
                            "confidence": api_result["confidence"],
                            "message": "License plate detected successfully (Plate Recognizer)"
                        }
                    else:
                        print(f"Plate Recognizer detected '{normalized}' but format invalid")
                else:
                    print(f"Plate Recognizer: {api_result['message']}")
            except Exception as e:
                print(f"Plate Recognizer error: {e}")
            
            # Option 2: Try OpenALPR Cloud API
            try:
                from app.services.openalpr_cloud_service import openalpr_cloud_service
                
                print("Trying OpenALPR Cloud API...")
                api_result = openalpr_cloud_service.recognize_plate(image_bytes, country="us")
                
                if api_result["success"]:
                    # Normalize and validate
                    normalized = normalize_vehicle_number(api_result["vehicle_number"])
                    
                    if validate_vehicle_format(normalized):
                        print(f"OpenALPR Cloud success: {normalized}")
                        return {
                            "success": True,
                            "vehicle_number": normalized,
                            "confidence": api_result["confidence"],
                            "message": "License plate detected successfully (OpenALPR Cloud)"
                        }
                    else:
                        print(f"OpenALPR Cloud detected '{normalized}' but format invalid")
                else:
                    print(f"OpenALPR Cloud: {api_result['message']}")
            except Exception as e:
                print(f"OpenALPR Cloud error: {e}")
            
            print("Cloud APIs not configured or failed, trying EasyOCR...")
            
            # Fallback to EasyOCR
            # Preprocess image (Requirement 4.2)
            preprocessed = self.preprocess_image(image_bytes)
            
            if preprocessed is None:
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": "Failed to preprocess image"
                }
            
            # Save preprocessed image to temporary file for ALPR processing
            # Requirement 17.1: Images stored temporarily
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file_path = temp_file.name
            cv2.imwrite(temp_file_path, preprocessed)
            temp_file.close()
            
            # Perform ALPR processing
            result = self._perform_alpr(temp_file_path)
            
            # Delete temporary file immediately (Requirement 4.12, 17.2)
            self._delete_image_file(temp_file_path)
            temp_file_path = None
            
            if not result["success"]:
                return result
            
            # Normalize extracted vehicle number (Requirement 4.10)
            normalized = normalize_vehicle_number(result["vehicle_number"])
            
            # Validate format (Requirement 4.11)
            if not validate_vehicle_format(normalized):
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": result["confidence"],
                    "message": f"Extracted text '{normalized}' is not a valid vehicle number format"
                }
            
            return {
                "success": True,
                "vehicle_number": normalized,
                "confidence": result["confidence"],
                "message": "Vehicle number extracted successfully"
            }
            
        except Exception as e:
            print(f"Error in ALPR processing: {e}")
            return {
                "success": False,
                "vehicle_number": None,
                "confidence": 0.0,
                "message": f"ALPR processing failed: {str(e)}"
            }
        
        finally:
            # Ensure temporary file is deleted (Requirement 17.2, 17.3)
            if temp_file_path and os.path.exists(temp_file_path):
                self._delete_image_file(temp_file_path)
    
    def _perform_alpr(self, image_path: str) -> Dict[str, Any]:
        """
        Perform ALPR on preprocessed image using EasyOCR library
        
        **Validates Requirements**: 4.7, 4.8, 4.9
        
        Args:
            image_path: Path to preprocessed image
            
        Returns:
            Dictionary with success, vehicle_number, and confidence
        """
        try:
            # Try to import EasyOCR first (recommended)
            try:
                import easyocr
                import cv2
                
                # Initialize EasyOCR reader (only once, cache it)
                if not hasattr(self, '_easyocr_reader'):
                    print("Initializing EasyOCR reader...")
                    self._easyocr_reader = easyocr.Reader(['en'], gpu=False)
                    print("EasyOCR reader initialized successfully")
                
                # Read the image
                img = cv2.imread(image_path)
                
                # Additional preprocessing for license plates
                # Convert to grayscale
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Apply bilateral filter to reduce noise while keeping edges sharp
                filtered = cv2.bilateralFilter(gray, 11, 17, 17)
                
                # Apply adaptive thresholding
                thresh = cv2.adaptiveThreshold(
                    filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
                
                # Save preprocessed image temporarily
                preprocessed_path = image_path.replace('.jpg', '_preprocessed.jpg')
                cv2.imwrite(preprocessed_path, thresh)
                
                # Read text from both original and preprocessed images
                results_original = self._easyocr_reader.readtext(image_path)
                results_preprocessed = self._easyocr_reader.readtext(preprocessed_path)
                
                # Delete preprocessed image
                try:
                    import os
                    os.remove(preprocessed_path)
                except:
                    pass
                
                # Combine results
                all_results = results_original + results_preprocessed
                
                if not all_results:
                    return {
                        "success": False,
                        "vehicle_number": None,
                        "confidence": 0.0,
                        "message": "No text detected in image"
                    }
                
                # Find result that matches vehicle number pattern
                best_result = None
                best_confidence = 0.0
                
                # Vehicle number patterns
                vehicle_patterns = [
                    r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$',  # Indian: MH12AB1234
                    r'^[A-Z]{3}[0-9]{4}$',                     # Simple: ABC1234
                    r'^[0-9]{2}[A-Z]{2}[0-9]{4}$',            # Alternative: 12AB3456
                    r'^[A-Z]{2}[0-9]{6}$',                     # Format: AB123456
                ]
                
                import re
                
                for (bbox, text, confidence) in all_results:
                    # Clean the text: remove spaces, special characters
                    cleaned_text = ''.join(c for c in text if c.isalnum()).upper()
                    
                    # Check length first (6-10 characters)
                    if not (6 <= len(cleaned_text) <= 10):
                        continue
                    
                    # Check if it matches any vehicle number pattern
                    matches_pattern = any(re.match(pattern, cleaned_text) for pattern in vehicle_patterns)
                    
                    if matches_pattern and confidence > best_confidence:
                        best_result = cleaned_text
                        best_confidence = confidence
                        print(f"Found potential vehicle number: {cleaned_text} (confidence: {confidence})")
                
                if best_result:
                    print(f"EasyOCR detected plate: {best_result} with confidence: {best_confidence}")
                    return {
                        "success": True,
                        "vehicle_number": best_result,
                        "confidence": best_confidence,
                        "message": "License plate detected successfully"
                    }
                else:
                    # No valid vehicle number pattern found
                    print("No valid vehicle number pattern detected in image")
                    return {
                        "success": False,
                        "vehicle_number": None,
                        "confidence": 0.0,
                        "message": "No vehicle number pattern detected. Please ensure the license plate is clearly visible and try again, or use manual entry."
                    }
                    
            except ImportError:
                print("EasyOCR not installed, trying OpenALPR...")
                pass
            
            # Fallback to OpenALPR if EasyOCR is not available
            try:
                from openalpr import Alpr
            except ImportError:
                print("OpenALPR library not installed. Install with: pip install openalpr")
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": "ALPR library not available"
                }
            
            # Initialize OpenALPR
            alpr = None
            try:
                alpr = Alpr("us", "/etc/openalpr/openalpr.conf", "/usr/share/openalpr/runtime_data")
                
                if not alpr.is_loaded():
                    print("Error loading OpenALPR")
                    return {
                        "success": False,
                        "vehicle_number": None,
                        "confidence": 0.0,
                        "message": "ALPR initialization failed"
                    }
                
                alpr.set_top_n(10)
                results = alpr.recognize_file(image_path)
                
                if not results or 'results' not in results:
                    return {
                        "success": False,
                        "vehicle_number": None,
                        "confidence": 0.0,
                        "message": "No license plate detected in image"
                    }
                
                plates = results['results']
                
                if len(plates) == 0:
                    return {
                        "success": False,
                        "vehicle_number": None,
                        "confidence": 0.0,
                        "message": "No license plate detected in image"
                    }
                
                best_plate = max(plates, key=lambda x: x['confidence'])
                plate_text = best_plate['plate']
                confidence = best_plate['confidence'] / 100.0
                
                print(f"ALPR detected plate: {plate_text} with confidence: {confidence}")
                
                return {
                    "success": True,
                    "vehicle_number": plate_text,
                    "confidence": confidence,
                    "message": "License plate detected successfully"
                }
                
            finally:
                if alpr:
                    alpr.unload()
            
        except Exception as e:
            print(f"ALPR processing error: {e}")
            return {
                "success": False,
                "vehicle_number": None,
                "confidence": 0.0,
                "message": f"ALPR processing failed: {str(e)}"
            }
    
    def _delete_image_file(self, file_path: str) -> None:
        """
        Delete image file immediately after processing
        
        **Validates Requirements**: 4.12, 17.1, 17.2, 17.3, 17.4, 17.5
        
        Args:
            file_path: Path to image file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted temporary image file: {file_path}")
        except Exception as e:
            print(f"Error deleting image file {file_path}: {e}")


# Service instance
alpr_service = ALPRService()
