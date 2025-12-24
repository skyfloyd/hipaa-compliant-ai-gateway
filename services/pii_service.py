"""
PII/PHI Detection and Removal Service using Presidio
Detects and removes Protected Health Information (PHI) and Personally Identifiable Information (PII)
"""

import uuid
import re
from typing import Dict, List, Optional
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from services.session_store import SessionStore

# Global session store instance
session_store = SessionStore(expiration_hours=24)


class PIIService:
    """Uses Presidio for PHI detection and de-identification"""
    
    def __init__(self):
        # Configure Presidio to use the medium spaCy model we installed
        # Using en_core_web_md for better accuracy with word vectors (~91 MB)
        # Create NLP engine provider with explicit model configuration
        nlp_configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_md"}]
        }
        
        nlp_engine_provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
        nlp_engine = nlp_engine_provider.create_engine()
        
        # Initialize analyzer with the configured NLP engine
        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        self._add_custom_recognizers()
    
    def _add_custom_recognizers(self):
        """Add custom recognizers for medical entities"""
        
        # Enhanced SSN recognizer - Presidio's default might miss some patterns
        ssn_patterns = [
            Pattern(
                name="ssn_pattern_1",
                regex=r"\b(?:SSN|Social Security Number|social security)[\s:]*(\d{3}-\d{2}-\d{4})\b",
                score=0.9
            ),
            Pattern(
                name="ssn_pattern_2",
                regex=r"\b\d{3}-\d{2}-\d{4}\b",  # Format: 123-45-6789
                score=0.85
            ),
            Pattern(
                name="ssn_pattern_3",
                regex=r"\b\d{3}\s\d{2}\s\d{4}\b",  # Format: 123 45 6789
                score=0.85
            ),
            Pattern(
                name="ssn_pattern_4",
                regex=r"\b\d{9}\b",  # Format: 123456789 (9 consecutive digits)
                score=0.7
            ),
        ]
        ssn_recognizer = PatternRecognizer(
            supported_entity="US_SSN",
            patterns=ssn_patterns
        )
        
        # Medical Record Number (MRN) recognizer - improved patterns
        mrn_patterns = [
            Pattern(
                name="mrn_pattern_1",
                regex=r"\b(?:MRN|Medical Record Number|Patient ID|Record #)[\s:#]*([A-Z0-9-]{5,15})\b",
                score=0.85
            ),
            Pattern(
                name="mrn_pattern_2",
                regex=r"\b[A-Z]{2,3}-\d{5,10}\b",  # Format: ABC-123456
                score=0.6
            ),
        ]
        mrn_recognizer = PatternRecognizer(
            supported_entity="MEDICAL_RECORD_NUMBER",
            patterns=mrn_patterns
        )
        
        # Enhanced Age recognizer with multiple patterns
        age_patterns = [
            Pattern(
                name="age_pattern_1",
                regex=r"\b(?:age|aged|Age|years old|year old|y\.?o\.?)[\s:]*(\d{2,3})\b",
                score=0.7
            ),
            Pattern(
                name="age_pattern_2",
                regex=r"\b(\d{2,3})-year-old\b",
                score=0.7
            ),
            Pattern(
                name="age_pattern_3",
                regex=r"\(age[:\s]+(\d{2,3})\)",
                score=0.7
            ),
        ]
        age_recognizer = PatternRecognizer(
            supported_entity="AGE",
            patterns=age_patterns
        )
        
        # Add custom recognizers to analyzer
        # Note: Adding SSN recognizer will override Presidio's default if it exists
        self.analyzer.registry.add_recognizer(ssn_recognizer)
        self.analyzer.registry.add_recognizer(mrn_recognizer)
        self.analyzer.registry.add_recognizer(age_recognizer)
    
    def _extract_age_from_text(self, text: str) -> Optional[int]:
        """Extract numeric age from detected age text"""
        # Extract all numbers from the text
        numbers = re.findall(r'\d{2,3}', text)
        if numbers:
            try:
                age = int(numbers[0])
                # Sanity check: age should be 0-120
                if 0 <= age <= 120:
                    return age
            except ValueError:
                pass
        return None
    
    def deidentify(self, text: str, session_id: str) -> tuple[str, List[Dict], Dict[str, str]]:
        """Analyze and de-identify PHI using Presidio"""
        
        # Analyze text for PII/PHI
        analyzer_results = self.analyzer.analyze(
            text=text,
            language='en',
            entities=[
                "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "DATE_TIME",
                "LOCATION", "US_SSN", "US_DRIVER_LICENSE",
                "MEDICAL_RECORD_NUMBER", "AGE", "CREDIT_CARD",
                "US_PASSPORT", "IP_ADDRESS", "IBAN_CODE", "URL"
            ]
        )
        
        # Filter results - ONLY filter ages that are 89 or under
        # Ages over 89 must ALWAYS be de-identified per HIPAA
        filtered_results = []
        for result in analyzer_results:
            if result.entity_type == "AGE":
                age_text = text[result.start:result.end]
                age = self._extract_age_from_text(age_text)
                
                if age is not None:
                    # HIPAA: Only de-identify if age > 89
                    if age > 89:
                        filtered_results.append(result)
                    # else: age <= 89, keep it in the text (don't de-identify)
                else:
                    # If we can't parse the age, be conservative and de-identify it
                    # Better safe than sorry for PHI
                    filtered_results.append(result)
            else:
                # All other entity types: always de-identify
                filtered_results.append(result)
        
        # Create tokens for replacement - use UUIDs for uniqueness
        tokens = {}
        
        # Sort by position (reverse) for proper replacement
        sorted_results = sorted(filtered_results, key=lambda x: x.start, reverse=True)
        
        deidentified_text = text
        for result in sorted_results:
            entity_type = result.entity_type
            original_value = text[result.start:result.end]
            
            # Generate unique token using UUID
            token = f"[{entity_type}_{uuid.uuid4().hex[:8]}]"
            tokens[token] = original_value
            
            # Replace in text
            deidentified_text = (
                deidentified_text[:result.start] +
                token +
                deidentified_text[result.end:]
            )
        
        # Store/update tokens for this session
        existing_tokens = session_store.get(session_id)
        if existing_tokens:
            tokens.update(existing_tokens)  # Merge with existing
        session_store.set(session_id, tokens)
        
        # Format detected entities for response
        detected_entities = [
            {
                "entity_type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score,
                "text": text[result.start:result.end]
            }
            for result in filtered_results
        ]
        
        return deidentified_text, detected_entities, tokens
    
    def reidentify(self, text: str, session_id: str) -> str:
        """Replace tokens back with original PHI"""
        tokens = session_store.get(session_id)
        if not tokens:
            return text
        
        reidentified = text
        for token, original_value in tokens.items():
            reidentified = reidentified.replace(token, original_value)
        
        return reidentified
    
    def detect_pii(self, text: str) -> list:
        """
        Detect all PII/PHI entities in the text using Presidio.
        This is a diagnostic method that doesn't perform de-identification.
        
        Args:
            text: Input text to scan
            
        Returns:
            List of detected entities with their positions and types
        """
        results = self.analyzer.analyze(
            text=text,
            language='en',
            entities=[
                "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "DATE_TIME",
                "LOCATION", "US_SSN", "US_DRIVER_LICENSE",
                "MEDICAL_RECORD_NUMBER", "AGE", "CREDIT_CARD",
                "US_PASSPORT", "IP_ADDRESS", "IBAN_CODE", "URL"
            ]
        )
        
        return [
            {
                'entity_type': result.entity_type,
                'start': result.start,
                'end': result.end,
                'score': result.score,
                'text': text[result.start:result.end]
            }
            for result in results
        ]
