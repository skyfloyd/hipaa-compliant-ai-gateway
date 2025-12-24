"""
HIPAA-Compliant AI Gateway
A FastAPI service that removes PII/PHI before sending to LLM and reinserts it in the response.

Created by Mher Aghabalyan
"""

import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
from services.pii_service import PIIService
from services.llm_service import LLMService

app = FastAPI(
    title="HIPAA-Compliant AI Gateway",
    description="Gateway that removes PII/PHI before LLM processing and reinserts it in responses",
    version="1.0.0"
)

# Initialize services
pii_service = PIIService()
llm_service = LLMService()


class PromptRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None
    model: Optional[str] = "gpt-3.5-turbo"


class PromptResponse(BaseModel):
    original_prompt: str
    deidentified_prompt: str
    llm_response: str
    reidentified_response: str
    detected_entities: List[Dict]
    tokens_used: Dict[str, str]
    session_id: str


class DetectPIIRequest(BaseModel):
    text: str


@app.get("/")
async def root():
    return {
        "message": "HIPAA-Compliant AI Gateway",
        "status": "operational",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/detect-pii")
async def detect_pii(request: DetectPIIRequest):
    """
    Diagnostic endpoint to detect PII/PHI in text without processing.
    Useful for testing and understanding what Presidio detects.
    """
    try:
        detected_entities = pii_service.detect_pii(request.text)
        return {
            "text": request.text,
            "entities_detected": len(detected_entities),
            "entities": detected_entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting PII: {str(e)}")


@app.post("/chat", response_model=PromptResponse)
async def chat(request: PromptRequest):
    """
    Process a chat request by:
    1. Detecting and removing PII/PHI from the prompt
    2. Sending sanitized prompt to LLM
    3. Reinserting PII/PHI into the LLM response
    4. Returning the final response
    
    Uses session-based token management for PHI reinsertion.
    """
    try:
        # Generate or use provided session_id
        session_id = request.session_id or str(uuid.uuid4())
        
        # Step 1: Detect and remove PII/PHI
        deidentified_prompt, detected_entities, tokens = pii_service.deidentify(
            request.prompt, 
            session_id
        )
        
        # Step 2: Send to LLM
        llm_response = await llm_service.get_completion(
            deidentified_prompt, 
            model=request.model
        )
        
        # Step 3: Reinsert PII/PHI using session_id
        reidentified_response = pii_service.reidentify(llm_response, session_id)
        
        return PromptResponse(
            original_prompt=request.prompt,
            deidentified_prompt=deidentified_prompt,
            llm_response=llm_response,
            reidentified_response=reidentified_response,
            detected_entities=detected_entities,
            tokens_used=tokens,
            session_id=session_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

