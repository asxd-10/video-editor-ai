"""
LLM Client Service
Handles communication with OpenRouter API (Gemini 3 Pro)
"""
import os
import json
import httpx
import asyncio
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for OpenRouter API (Gemini 3 Pro Image Preview)
    Handles API calls, error handling, retries, and response parsing
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "google/gemini-3-pro-image-preview",
        timeout: int = 120,
        max_retries: int = 3
    ):
        """
        Args:
            api_key: OpenRouter API key (from env if None)
            base_url: OpenRouter API base URL
            model: Model name
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key or os.getenv("OPENROUTER_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_KEY not found in environment variables")
        
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://video-editor-ai.local",  # Optional: for analytics
                "X-Title": "Video Editor AI",  # Optional: for analytics
                "Content-Type": "application/json"
            }
        )
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate response from LLM.
        
        Args:
            messages: List of {role: "user"/"assistant", content: "..."}
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            response_format: Optional JSON schema for structured output
        
        Returns:
            {
                "content": str,
                "usage": {"prompt_tokens": int, "completion_tokens": int},
                "model": str
            }
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add response format if specified (for structured output)
        if response_format:
            payload["response_format"] = response_format
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Extract content
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                
                logger.info(
                    f"LLM request successful: "
                    f"{usage.get('prompt_tokens', 0)} prompt tokens, "
                    f"{usage.get('completion_tokens', 0)} completion tokens"
                )
                
                return {
                    "content": content,
                    "usage": usage,
                    "model": data.get("model", self.model)
                }
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code >= 500:  # Server error
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Server error, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                raise
            except Exception as e:
                logger.error(f"LLM request failed: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise
        
        raise Exception(f"LLM request failed after {self.max_retries} attempts")
    
    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        json_schema: Dict[str, Any],
        temperature: float = 0.3  # Lower temperature for structured output
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response.
        
        Args:
            messages: Prompt messages
            json_schema: JSON schema for response format
            temperature: Lower temperature for more consistent output
        
        Returns:
            Parsed JSON response
        """
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "storytelling_edit_plan",
                "strict": True,
                "schema": json_schema
            }
        }
        
        response = await self.generate(
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        
        # Parse JSON from response
        try:
            content = response["content"]
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.error(f"Response content: {content[:500]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'client'):
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.client.aclose())
                else:
                    loop.run_until_complete(self.client.aclose())
            except:
                pass

