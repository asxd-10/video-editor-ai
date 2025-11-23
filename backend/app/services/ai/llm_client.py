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
        
        # Increase max_tokens to prevent truncation (especially for multi-video edits)
        # Default to 6000 to handle larger responses
        response = await self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=6000,  # Increased from 4000 to handle multi-video responses
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
            
            # Try to parse JSON
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            
            # Log error position and context
            error_pos = getattr(e, 'pos', None)
            if error_pos:
                start = max(0, error_pos - 200)
                end = min(len(content), error_pos + 200)
                logger.error(f"Error at position {error_pos} (char {error_pos} of {len(content)})")
                logger.error(f"Context around error:\n{content[start:end]}")
            else:
                logger.error(f"Response content (first 3000 chars):\n{content[:3000]}")
            
            # Try to repair common JSON issues
            try:
                repaired = self._repair_json(content)
                parsed = json.loads(repaired)
                logger.warning("Successfully repaired JSON response")
                return parsed
            except Exception as repair_error:
                logger.error(f"JSON repair also failed: {repair_error}")
                # Log the full response length and a sample
                logger.error(f"Full response length: {len(content)} characters")
                if len(content) > 3000:
                    logger.error(f"Response sample (last 1000 chars):\n{content[-1000:]}")
                raise ValueError(f"Invalid JSON response from LLM: {e}")
    
    def _repair_json(self, content: str) -> str:
        """
        Attempt to repair common JSON issues:
        - Truncated responses (missing closing brackets/braces)
        - Trailing commas
        Note: Unterminated strings are harder to fix automatically and may require
        regenerating the response with higher max_tokens.
        """
        import re
        
        repaired = content
        
        # Fix 1: Remove trailing commas before closing brackets/braces
        repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)
        
        # Fix 2: Close unclosed structures (common with truncated responses)
        open_braces = repaired.count('{')
        close_braces = repaired.count('}')
        open_brackets = repaired.count('[')
        close_brackets = repaired.count(']')
        
        # Only close if we're clearly missing closing brackets
        # This helps with truncated responses
        if open_braces > close_braces:
            repaired += '\n' + '}' * (open_braces - close_braces)
        if open_brackets > close_brackets:
            repaired += '\n' + ']' * (open_brackets - close_brackets)
        
        # Note: Unterminated strings are more complex to fix automatically
        # If repair fails, the error logging will show the exact position
        # and the user may need to increase max_tokens or adjust the prompt
        
        return repaired
    
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

