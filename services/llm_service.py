"""
LLM Service
Handles communication with Large Language Models
"""

import os
import httpx
from typing import Optional


class LLMService:
    """
    Service for interacting with LLM APIs.
    Supports OpenAI-compatible APIs.
    """
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.default_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-3.5-turbo")
        
        if not self.api_key:
            # For demo purposes, use a mock response if no API key is set
            self.use_mock = True
        else:
            self.use_mock = False
    
    async def get_completion(
        self, 
        prompt: str, 
        model: Optional[str] = None
    ) -> str:
        """
        Get completion from LLM.
        
        Args:
            prompt: The sanitized prompt (without PII/PHI)
            model: Model name (optional)
            
        Returns:
            LLM response text
        """
        model = model or self.default_model
        
        if self.use_mock:
            # Mock response for demo purposes
            return self._get_mock_response(prompt)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        
        except httpx.HTTPError as e:
            # Fallback to mock if API call fails
            print(f"LLM API error: {e}. Using mock response.")
            return self._get_mock_response(prompt)
    
    def _get_mock_response(self, prompt: str) -> str:
        """
        Generate a mock response for demo purposes.
        This simulates an LLM response without making actual API calls.
        """
        # Simple mock that acknowledges the sanitized prompt
        return f"I understand your request. You mentioned some placeholders like [SSN_0] or [PHONE_0]. " \
               f"Based on your query, I can help you with healthcare-related information. " \
               f"Please note that I'm processing this in a HIPAA-compliant manner."

