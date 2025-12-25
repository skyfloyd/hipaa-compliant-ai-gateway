"""
LLM Service
Handles communication with Google Gemini API using official library
"""

import os
import asyncio
from typing import Optional
import google.generativeai as genai


class LLMService:
    """
    Service for interacting with Google Gemini API.
    Uses the official google-generativeai library.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        
        if not self.api_key:
            # For demo purposes, use a mock response if no API key is set
            self.use_mock = True
            self.model = None
        else:
            self.use_mock = False
            # Configure the Gemini API
            genai.configure(api_key=self.api_key)
            # Use gemini-2.5-flash (free tier, fast, current model)
            # Alternative: gemini-2.5-pro for better quality
            self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    async def get_completion(
        self, 
        prompt: str, 
        model: Optional[str] = None
    ) -> str:
        """
        Get completion from Google Gemini.
        
        Args:
            prompt: The sanitized prompt (without PII/PHI)
            model: Model name (ignored - using gemini-2.5-flash)
            
        Returns:
            LLM response text
        """
        if self.use_mock:
            # Mock response for demo purposes
            return self._get_mock_response(prompt)
        
        try:
            # Run the synchronous Gemini API call in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=2048,  # Increased from 1000 to allow longer responses
                    )
                )
            )
            
            # Extract text from response
            if response.text:
                return response.text
            else:
                raise ValueError("Empty response from Gemini API")
        
        except Exception as e:
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
