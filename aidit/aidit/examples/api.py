"""
FastAPI application for chatting with phi-4 model via OpenRouter
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
import requests
import os
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Phi-4 Chat API", version="1.0.0")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get API key from environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Please set OPENROUTER_API_KEY environment variable")

# OpenRouter API endpoint
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default model - adjust based on available models
# Options: "microsoft/phi-4", "nextbit/phi-4-int4", etc.
DEFAULT_MODEL = "microsoft/phi-4"


class Message(BaseModel):
    role: str  # "user", "assistant", or "system"
    content: Union[str, List[Dict[str, Any]]]  # Can be text or multimodal content


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = DEFAULT_MODEL
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000


class ChatResponse(BaseModel):
    response: str
    model: str
    usage: Optional[dict] = None


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Phi-4 Chat API",
        "model": DEFAULT_MODEL
    }


@app.get("/models")
async def get_models():
    """Get available models from OpenRouter"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}")


def encode_image_to_base64(image_file: bytes) -> str:
    """Convert image bytes to base64 data URL"""
    base64_image = base64.b64encode(image_file).decode('utf-8')
    # Try to detect image type
    img = Image.open(BytesIO(image_file))
    format_map = {
        'JPEG': 'image/jpeg',
        'PNG': 'image/png',
        'GIF': 'image/gif',
        'WEBP': 'image/webp'
    }
    img_format = format_map.get(img.format, 'image/jpeg')
    return f"data:{img_format};base64,{base64_image}"


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with phi-4 model via OpenRouter (supports text and images)
    
    Example request with text:
    {
        "messages": [
            {"role": "user", "content": "Hello! What can you do?"}
        ],
        "model": "microsoft/phi-4",
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    Example request with image (base64):
    {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ..."}}
                ]
            }
        ]
    }
    """
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        
        # Convert Pydantic models to dict
        # Handle both string content and multimodal content
        messages = []
        for msg in request.messages:
            message_dict = {"role": msg.role}
            if isinstance(msg.content, str):
                message_dict["content"] = msg.content
            else:
                # Multimodal content (list of content parts)
                message_dict["content"] = msg.content
            messages.append(message_dict)
        
        data = {
            "model": request.model or DEFAULT_MODEL,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract the response text
        if "choices" in result and len(result["choices"]) > 0:
            response_text = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            
            return ChatResponse(
                response=response_text,
                model=result.get("model", request.model or DEFAULT_MODEL),
                usage=usage
            )
        else:
            raise HTTPException(status_code=500, detail="No response from model")
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"OpenRouter API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/chat/with-image")
async def chat_with_image(
    message: str = Form(...),
    image: UploadFile = File(...),
    model: Optional[str] = Form(DEFAULT_MODEL),
    temperature: Optional[float] = Form(0.7),
    max_tokens: Optional[int] = Form(1000)
):
    """
    Chat endpoint that accepts an image file upload along with text
    
    Example using curl:
    curl -X POST "http://localhost:8000/chat/with-image" \
      -F "message=What's in this image?" \
      -F "image=@frame_1.jpg" \
      -F "model=microsoft/phi-4"
    """
    try:
        # Read and encode the image
        image_bytes = await image.read()
        base64_image = encode_image_to_base64(image_bytes)
        
        # Prepare the message with image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {
                        "type": "image_url",
                        "image_url": {"url": base64_image}
                    }
                ]
            }
        ]
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": model or DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return {
                "response": result["choices"][0]["message"]["content"],
                "model": result.get("model", model or DEFAULT_MODEL),
                "usage": result.get("usage", {})
            }
        else:
            raise HTTPException(status_code=500, detail="No response from model")
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"OpenRouter API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/chat/simple")
async def chat_simple(message: str, model: Optional[str] = DEFAULT_MODEL):
    """
    Simplified chat endpoint - just send a message string
    
    Example: POST /chat/simple?message=Hello&model=microsoft/phi-4
    """
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": model or DEFAULT_MODEL,
            "messages": [
                {"role": "user", "content": message}
            ],
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return {
                "response": result["choices"][0]["message"]["content"],
                "model": result.get("model", model or DEFAULT_MODEL)
            }
        else:
            raise HTTPException(status_code=500, detail="No response from model")
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"OpenRouter API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/chat/image-base64")
async def chat_with_base64_image(
    message: str,
    image_base64: str,
    model: Optional[str] = DEFAULT_MODEL,
    temperature: Optional[float] = 0.7,
    max_tokens: Optional[int] = 1000
):
    """
    Chat endpoint that accepts base64 encoded image
    
    Example request:
    {
        "message": "What's in this image?",
        "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
        "model": "microsoft/phi-4"
    }
    """
    try:
        # Ensure the base64 string has the data URL prefix
        if not image_base64.startswith("data:"):
            image_base64 = f"data:image/jpeg;base64,{image_base64}"
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_base64}
                    }
                ]
            }
        ]
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": model or DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return {
                "response": result["choices"][0]["message"]["content"],
                "model": result.get("model", model or DEFAULT_MODEL),
                "usage": result.get("usage", {})
            }
        else:
            raise HTTPException(status_code=500, detail="No response from model")
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"OpenRouter API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

