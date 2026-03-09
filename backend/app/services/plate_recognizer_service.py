"""
Plate Recognizer API service for accurate license plate recognition

This service uses Plate Recognizer API (https://platerecognizer.com/)
which provides 95%+ accuracy for license plate detection.

Free tier: 2,500 API calls per month
"""
import requests
import base64
from typing import Dict, Any, Optional


class PlateRecognizerService:
    """Service for license plate recognition using Plate Recognizer API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Plate Recognizer service
        
        Args:
            api_key: Plate Recognizer API key (get from https://app.platerecognizer.com/)
        """
        self.api_key = api_key or "076f00c3821c254afd6301db21fa2d20df64057c"
        self.api_url = "https://api.platerecognizer.com/v1/plate-reader/"
        
    def recognize_plate(self, image_data: bytes) -> Dict[str, Any]:
        """
        Recognize license plate from image using Plate Recognizer API
        
        Args:
            image_data: Image bytes
            
        Returns:
            Dictionary with:
                - success: bool
                - vehicle_number: str (if found)
                - confidence: float (0-1)
                - message: str
        """
        try:
            # Check if API key is configured
            if self.api_key == "YOUR_API_KEY_HERE":
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": "Plate Recognizer API key not configured. Please add your API key to use this service."
                }
            
            # Prepare the request
            headers = {
                'Authorization': f'Token {self.api_key}'
            }
            
            files = {
                'upload': ('image.jpg', image_data, 'image/jpeg')
            }
            
            # Optional: Specify regions for better accuracy
            # data = {'regions': ['in', 'us']}  # India, US
            
            # Make API request
            response = requests.post(
                self.api_url,
                headers=headers,
                files=files,
                timeout=10
            )
            
            if response.status_code != 200 and response.status_code != 201:
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": f"API error: {response.status_code} - {response.text}"
                }
            
            result = response.json()
            
            # Check if any plates were detected
            if not result.get('results') or len(result['results']) == 0:
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": "No license plate detected in image"
                }
            
            # Get the best result (highest confidence)
            best_result = max(result['results'], key=lambda x: x.get('score', 0))
            
            plate_text = best_result.get('plate', '').upper().replace(' ', '')
            confidence = best_result.get('score', 0.0)
            
            if not plate_text:
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": "Could not read license plate text"
                }
            
            print(f"Plate Recognizer detected: {plate_text} with confidence: {confidence}")
            
            return {
                "success": True,
                "vehicle_number": plate_text,
                "confidence": confidence,
                "message": "License plate detected successfully"
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "vehicle_number": None,
                "confidence": 0.0,
                "message": "API request timeout. Please try again."
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "vehicle_number": None,
                "confidence": 0.0,
                "message": f"Network error: {str(e)}"
            }
        except Exception as e:
            print(f"Plate Recognizer error: {e}")
            return {
                "success": False,
                "vehicle_number": None,
                "confidence": 0.0,
                "message": f"Recognition failed: {str(e)}"
            }


# Service instance
plate_recognizer_service = PlateRecognizerService()
