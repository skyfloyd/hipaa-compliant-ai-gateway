"""
PII/PHI Reinsertion Service
Reinserts PII/PHI data back into LLM responses
"""

import re
from typing import Dict


class ReinsertionService:
    """
    Service for reinserting PII/PHI into LLM responses.
    Replaces placeholders with original values.
    """
    
    def __init__(self):
        # Pattern to match Presidio-style placeholders: [ENTITY_TYPE_NUMBER]
        self.placeholder_pattern = re.compile(r'\[([A-Z_]+)_(\d+)\]')
    
    def reinsert_pii(self, text: str, pii_map: Dict[str, str]) -> str:
        """
        Reinsert PII/PHI into text by replacing placeholders with original values.
        
        Args:
            text: LLM response text containing placeholders
            pii_map: Dictionary mapping placeholders to original PII/PHI values
            
        Returns:
            Text with PII/PHI reinserted
        """
        result = text
        
        # Replace all placeholders with their original values
        # Sort by placeholder length (longest first) to avoid partial replacements
        sorted_placeholders = sorted(pii_map.keys(), key=len, reverse=True)
        
        for placeholder in sorted_placeholders:
            if placeholder in result:
                result = result.replace(placeholder, pii_map[placeholder])
        
        return result
