"""
VideoIndex class for handling API calls to LLM
"""
import requests
import os
import base64
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class VideoIndex:
    """
    Overarching class for handling API calls to LLM
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "google/gemini-2.0-flash-001"):
        self.api_key = api_key or os.getenv("OPENROUTER_KEY") or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_KEY or OPENROUTER_API_KEY must be set")
        
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def process_image_from_url(self, image_url: str, prompt: str = "What's in this image?") -> Dict[str, Any]:
        """
        Process an image from URL using the LLM API
        
        Args:
            image_url: URL of the image to process
            prompt: The prompt/question to ask about the image
            
        Returns:
            Dictionary with response, model, and usage information
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ]
            
            payload = {
                "model": self.model,
                "messages": messages
            }
            
            logger.info(f"Calling LLM API for image: {image_url[:50]}...")
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return {
                    "response": result["choices"][0]["message"]["content"],
                    "model": result.get("model", self.model),
                    "usage": result.get("usage", {})
                }
            else:
                raise ValueError("No response from model")
                
        except Exception as e:
            logger.error(f"Error processing image from URL: {str(e)}")
            raise
    
    def process_image_from_base64(self, base64_image: str, prompt: str = "What's in this image?") -> Dict[str, Any]:
        """
        Process an image from base64 string using the LLM API
        
        Args:
            base64_image: Base64 encoded image (with or without data URL prefix)
            prompt: The prompt/question to ask about the image
            
        Returns:
            Dictionary with response, model, and usage information
        """
        try:
            # Ensure base64 string has data URL prefix
            if not base64_image.startswith("data:"):
                base64_image = f"data:image/jpeg;base64,{base64_image}"
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": base64_image
                            }
                        }
                    ]
                }
            ]
            
            payload = {
                "model": self.model,
                "messages": messages
            }
            
            logger.info("Calling LLM API for base64 image")
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return {
                    "response": result["choices"][0]["message"]["content"],
                    "model": result.get("model", self.model),
                    "usage": result.get("usage", {})
                }
            else:
                raise ValueError("No response from model")
                
        except Exception as e:
            logger.error(f"Error processing base64 image: {str(e)}")
            raise

