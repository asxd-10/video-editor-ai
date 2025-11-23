"""
Utility functions for image processing
"""
import base64
from io import BytesIO
from PIL import Image


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 data URL"""
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    try:
        img = Image.open(BytesIO(image_bytes))
        format_map = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png',
            'GIF': 'image/gif',
            'WEBP': 'image/webp'
        }
        img_format = format_map.get(img.format, 'image/jpeg')
    except:
        img_format = 'image/jpeg'
    return f"data:{img_format};base64,{base64_image}"

