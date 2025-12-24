# HIPAA-Compliant AI Gateway

**Created by Mher Aghabalyan**

A FastAPI-based service that ensures HIPAA compliance when processing healthcare-related prompts through Large Language Models (LLMs). The gateway automatically detects and removes Protected Health Information (PHI) and Personally Identifiable Information (PII) before sending requests to LLMs, then reinserts the data into responses.

## Features

- **Advanced PII/PHI Detection with Presidio**: Uses Microsoft's Presidio framework for sophisticated NLP-based detection of sensitive information:
  - Person names (PERSON)
  - Email addresses (EMAIL_ADDRESS)
  - Phone numbers (PHONE_NUMBER)
  - Social Security Numbers (US_SSN)
  - Credit card numbers (CREDIT_CARD)
  - IP addresses (IP_ADDRESS)
  - Dates and times (DATE_TIME)
  - Locations and addresses (LOCATION)
  - Passport numbers (US_PASSPORT)
  - Driver license numbers (US_DRIVER_LICENSE)
  - Bank account numbers (IBAN_CODE, US_BANK_NUMBER)
  - Medical Record Numbers (MEDICAL_RECORD_NUMBER) - custom patterns
  - Age (AGE) - with HIPAA-compliant filtering (only ages > 89 are de-identified)
  - URLs
  - Organization names (ORGANIZATION)

- **HIPAA-Compliant Age Handling**: Ages 89 and under are preserved (not de-identified) per HIPAA Safe Harbor rules
- **Session-Based Token Management**: Thread-safe session storage with automatic expiration (24 hours)
- **Secure Processing**: Removes sensitive data before LLM processing using UUID-based tokens
- **Data Reinsertion**: Automatically reinserts PII/PHI into LLM responses using session tokens
- **Google Gemini Integration**: Uses Google's free Gemini Pro model for text generation
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Diagnostic Endpoint**: Test PII/PHI detection without processing through LLM

## Architecture

```
User Prompt (with PII/PHI)
    ↓
[PII Detection & Removal]
    ↓
Sanitized Prompt (with placeholders)
    ↓
[LLM Service]
    ↓
LLM Response (with placeholders)
    ↓
[PII Reinsertion]
    ↓
Final Response (with original PII/PHI)
```

## Quick Start

### Using Docker Compose

1. **Clone and navigate to the project:**
   ```bash
   cd hipaa-compliant-ai-gateway
   ```

2. **Set environment variables (optional):**
   ```bash
   export GEMINI_API_KEY=your-gemini-api-key-here  # Optional, defaults to provided key
   ```

3. **Start the service:**
   ```bash
   docker-compose up --build
   ```

4. **The service will be available at:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Using Docker

```bash
docker build -t hipaa-gateway .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-api-key \
  hipaa-gateway
```

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

3. **Run the application:**
   ```bash
   python main.py
   # or
   uvicorn main:app --reload
   ```

## API Usage

### Chat Endpoint

Send a POST request to `/chat` with a prompt. The service uses session-based token management:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Patient John Doe, SSN 123-45-6789, phone 555-123-4567, needs a follow-up appointment.",
    "session_id": "optional-session-id"
  }'
```

**Response:**
```json
{
  "original_prompt": "Patient John Doe, SSN 123-45-6789, phone 555-123-4567, needs a follow-up appointment.",
  "deidentified_prompt": "Patient [PERSON_abc12345], SSN [US_SSN_def67890], phone [PHONE_NUMBER_ghi23456], needs a follow-up appointment.",
  "llm_response": "I understand. [PERSON_abc12345] with [US_SSN_def67890] needs a follow-up...",
  "reidentified_response": "I understand. John Doe with SSN 123-45-6789 needs a follow-up...",
  "detected_entities": [
    {"entity_type": "PERSON", "start": 8, "end": 17, "score": 0.85, "text": "John Doe"},
    {"entity_type": "US_SSN", "start": 23, "end": 33, "score": 0.9, "text": "123-45-6789"},
    {"entity_type": "PHONE_NUMBER", "start": 41, "end": 53, "score": 0.85, "text": "555-123-4567"}
  ],
  "tokens_used": {
    "[PERSON_abc12345]": "John Doe",
    "[US_SSN_def67890]": "123-45-6789",
    "[PHONE_NUMBER_ghi23456]": "555-123-4567"
  },
  "session_id": "optional-session-id"
}
```

**Note**: If you don't provide a `session_id`, one will be automatically generated. Use the same `session_id` for multiple requests in the same conversation to maintain PHI token consistency.

### Example with Python

```python
import requests
import uuid

# Generate a session ID for the conversation
session_id = str(uuid.uuid4())

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "prompt": "My patient with email john@example.com and MRN 12345 needs medication review.",
        "session_id": session_id
    }
)

data = response.json()
print(f"Reidentified Response: {data['reidentified_response']}")
print(f"Deidentified Prompt: {data['deidentified_prompt']}")
print(f"Detected Entities: {len(data['detected_entities'])}")
print(f"Session ID: {data['session_id']}")
```

### Test PII Detection

You can test what PII/PHI Presidio detects without sending to LLM:

```bash
curl -X POST "http://localhost:8000/detect-pii" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient John Doe, SSN 123-45-6789, phone 555-123-4567, email john@example.com, needs follow-up."
  }'
```

## Mock Mode

If no `GEMINI_API_KEY` is provided, the service will operate in mock mode, returning simulated responses. This is useful for testing and demonstration purposes. The default configuration includes a Gemini API key, so the service will use the real Gemini API by default.

## Security Considerations

⚠️ **Important**: This is a demo project. For production use:

1. **Encryption**: Implement end-to-end encryption for data in transit
2. **Access Control**: Add authentication and authorization
3. **Audit Logging**: Implement comprehensive audit trails
4. **Data Storage**: Ensure no PII/PHI is logged or stored
5. **Compliance**: Review with legal/compliance teams for full HIPAA compliance
6. **Enhanced Detection**: Customize Presidio recognizers for domain-specific patterns (e.g., MRN formats)
7. **Tokenization**: Consider using secure tokenization instead of simple placeholders
8. **Model Training**: Fine-tune Presidio's models for your specific use case

## Project Structure

```
hipaa-compliant-ai-gateway/
├── main.py                 # FastAPI application
├── services/
│   ├── __init__.py
│   ├── pii_service.py     # PII/PHI detection, de-identification, and re-identification
│   ├── llm_service.py     # LLM integration
│   └── session_store.py   # Thread-safe session storage for PHI tokens
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (optional, defaults to provided key)

## Author

**Mher Aghabalyan**

## License

This is a demo project for educational purposes.

