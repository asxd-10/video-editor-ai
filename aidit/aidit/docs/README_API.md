# Phi-4 Chat API with OpenRouter

FastAPI interface for chatting with Microsoft Phi-4 model via OpenRouter.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenRouter API key:
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```
OPENROUTER_API_KEY=your-api-key-here
```

3. Run the API server:
```bash
python api.py
```

Or with uvicorn:
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### GET `/`
Health check endpoint

### GET `/models`
Get available models from OpenRouter

### POST `/chat`
Full chat endpoint with conversation history

**Request:**
```json
{
    "messages": [
        {"role": "user", "content": "Hello! What can you do?"}
    ],
    "model": "microsoft/phi-4",
    "temperature": 0.7,
    "max_tokens": 1000
}
```

**Response:**
```json
{
    "response": "I'm Phi-4, a language model...",
    "model": "microsoft/phi-4",
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 50
    }
}
```

### POST `/chat/simple?message=Hello&model=microsoft/phi-4`
Simplified endpoint - just send a message string

## Example Usage

### Using curl:
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello! Introduce yourself."}
    ]
  }'
```

### Using Python:
```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "messages": [
            {"role": "user", "content": "What is machine learning?"}
        ]
    }
)
print(response.json()["response"])
```

## Interactive API Docs

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Model Options

You can use different phi-4 variants by specifying the model:
- `microsoft/phi-4` (default)
- `nextbit/phi-4-int4` (if available)
- Check available models at `/models` endpoint

