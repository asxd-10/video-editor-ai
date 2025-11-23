import requests
import json
import os
import dotenv
dotenv.load_dotenv()
API_KEY_REF = os.getenv("OPENROUTER_KEY")

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY_REF}", 
    "Content-Type": "application/json"
}

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "What's in this image?"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                }
            }
        ]
    }
]

payload = {
    "model": "google/gemini-2.0-flash-001",
    "messages": messages
}

response = requests.post(url, headers=headers, json=payload)
print(response.json())
