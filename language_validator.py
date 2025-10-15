"""
Language validation service using FastText API
"""
import requests
from typing import List, Tuple, Dict
from config import FASTTEXT_API_URL, FASTTEXT_API_KEY

class LanguageValidator:
    """Validates language of words using FastText API"""
    
    def __init__(self):
        """Initialize FastText API connection"""
        self.api_url = FASTTEXT_API_URL
        self.api_key = FASTTEXT_API_KEY
    
    def validate_word_pairs(self, word_pairs: List[Tuple[str, str]], 
                           native_language: str, target_language: str) -> Dict:
        """
        Validate word pairs and return validation results
        
        Returns:
            {
                "valid_pairs": [(word1, word2), ...],
                "invalid_pairs": [(word1, word2, error), ...],
                "error_rate": float
            }
        """
        if not self.api_url or not self.api_key:
            # If no FastText API available, return all as valid
            return {
                "valid_pairs": word_pairs,
                "invalid_pairs": [],
                "error_rate": 0.0
            }
        
        valid_pairs = []
        invalid_pairs = []
        
        for native_word, target_word in word_pairs:
            try:
                # Validate native word
                native_valid = self._validate_single_word(native_word, native_language)
                # Validate target word
                target_valid = self._validate_single_word(target_word, target_language)
                
                if native_valid and target_valid:
                    valid_pairs.append((native_word, target_word))
                else:
                    error_msg = []
                    if not native_valid:
                        error_msg.append(f"'{native_word}' not in {native_language}")
                    if not target_valid:
                        error_msg.append(f"'{target_word}' not in {target_language}")
                    
                    invalid_pairs.append((native_word, target_word, "; ".join(error_msg)))
                    
            except Exception as e:
                # If validation fails, treat as invalid
                invalid_pairs.append((native_word, target_word, f"Validation error: {str(e)}"))
        
        error_rate = len(invalid_pairs) / len(word_pairs) if word_pairs else 0
        
        return {
            "valid_pairs": valid_pairs,
            "invalid_pairs": invalid_pairs,
            "error_rate": error_rate
        }
    
    def _validate_single_word(self, word: str, expected_language: str) -> bool:
        """Validate a single word against expected language"""
        try:
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "text": word,
                "expected_language": expected_language
            }
            
            response = requests.post(
                f"{self.api_url}/validate",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("is_valid", False)
            else:
                # If API fails, assume valid to not block import
                return True
                
        except Exception as e:
            print(f"Error validating word '{word}': {e}")
            # If validation fails, assume valid to not block import
            return True
    
    def detect_language(self, text: str) -> str:
        """Detect language of given text"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {"text": text}
            
            response = requests.post(
                f"{self.api_url}/detect",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("language", "unknown")
            else:
                return "unknown"
                
        except Exception as e:
            print(f"Error detecting language: {e}")
            return "unknown"
