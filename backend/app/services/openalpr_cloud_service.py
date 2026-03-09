"""
OpenALPR Cloud API service for accurate license plate recognition

This service uses OpenALPR Cloud API (https://cloud.openalpr.com/)
which provides 95%+ accuracy for license plate detection.

Free tier: 1,000 API calls per month
"""
import requests
import base64
from typing import Dict, Any, Optional


class OpenALPRCloudService:
    """Service for license plate recognition using OpenALPR Cloud API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenALPR Cloud service
        
        Args:
            api_key: OpenALPR Cloud API secret key (get from https://cloud.openalpr.com/)
        """
        self.api_key = api_key or "YOUR_OPENALPR_API_KEY_HERE"  # Replace with your API key
        self.api_url = "https://api.openalpr.com/v3/recognize"
        
    def recognize_plate(self, image_data: bytes, country: str = "us") -> Dict[str, Any]:
        """
        Recognize license plate from image using OpenALPR Cloud API
        
        Args:
            image_data: Image bytes
            country: Country code (us, eu, in, au, etc.)
            
        Returns:
            Dictionary with:
                - success: bool
                - vehicle_number: str (if found)
                - confidence: float (0-1)
                - message: str
        """
        try:
            # Check if API key is configured
            if self.api_key == "YOUR_OPENALPR_API_KEY_HERE":
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": "OpenALPR Cloud API key not configured. Please add your API key to use this service."
                }
            
            # Convert image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare the request
            params = {
                'secret_key': self.api_key,
                'recognize_vehicle': '0',  # Set to 1 if you want vehicle make/model
                'country': country,
                'return_image': '0',
                'topn': '10'
            }
            
            data = {
                'image_bytes': image_base64
            }
            
            # Make API request
            response = requests.post(
                self.api_url,
                data=data,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
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
            best_result = result['results'][0]
            
            if not best_result.get('candidates') or len(best_result['candidates']) == 0:
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": "Could not read license plate text"
                }
            
            # Get the top candidate
            top_candidate = best_result['candidates'][0]
            
            plate_text = top_candidate.get('plate', '').upper().replace(' ', '')
            confidence = top_candidate.get('confidence', 0.0) / 100.0  # Convert to 0-1 range
            
            if not plate_text:
                return {
                    "success": False,
                    "vehicle_number": None,
                    "confidence": 0.0,
                    "message": "Could not read license plate text"
                }
            
            print(f"OpenALPR Cloud detected: {plate_text} with confidence: {confidence}")
            
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
            print(f"OpenALPR Cloud error: {e}")
            return {
                "success": False,
                "vehicle_number": None,
                "confidence": 0.0,
                "message": f"Recognition failed: {str(e)}"
            }


# Service instance
openalpr_cloud_service = OpenALPRCloudService()
