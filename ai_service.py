"""
AI service for sentence generation and error analysis using LangChain
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from typing import List, Dict, Optional, Tuple
from config import OPENAI_API_KEY, TASK_PROBABILITIES
import random
import json

class AIService:
    """Handles AI operations for sentence generation and error analysis"""
    
    def __init__(self):
        """Initialize LangChain ChatOpenAI client"""
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key must be provided")
        
        # Initialize LangChain ChatOpenAI client
        self.llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=100
        )
        
        # Initialize GPT-4 for more complex analysis
        self.llm_advanced = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-4",
            temperature=0.3,
            max_tokens=200
        )
    
# ----------------------------- Sentence Generation -----------------------------

    def generate_sentence(self, target_word: str, user_preferred_topics: List[str], 
                         user_errors: List[Dict], target_language: str) -> Optional[str]:
        """Generate a sentence containing the target word using LangChain"""
        try:
            # Create topics string
            topics_str = ", ".join(user_preferred_topics) if user_preferred_topics else "general topics"
            
            # Simple prompt for sentence generation
            prompt = f"""Generate a natural sentence in {target_language} that:
1. Contains the word "{target_word}" in its correct grammatical form
2. Is related to these topics: {topics_str}
3. Is appropriate for language learning (not too complex)
4. Is grammatically correct and natural
5. Use only {target_language} words, no other languages

Return only the sentence, nothing else."""

            # Generate response using LangChain
            response = self.llm.invoke(prompt)
            result = response.content.strip()
            
            # Clean up the result
            if result:
                # Remove any quotes or extra formatting
                result = result.strip('"').strip("'").strip()
                return result
            
            return None
            
        except Exception as e:
            print(f"Error generating sentence: {e}")
            return None
    



    def analyze_answer(self, user_answer: str, correct_answer: str, 
                      target_language: str) -> Dict:
        """Analyze user's answer and determine if it's correct, morphological error, or synonym"""
        try:
            # Simple string comparison first
            user_clean = user_answer.lower().strip()
            correct_clean = correct_answer.lower().strip()
            
            if user_clean == correct_clean:
                return {
                    "is_correct": True,
                    "is_morphological_error": False,
                    "is_synonym": False,
                    "explanation": "Правильный ответ"
                }
            
            # Check for morphological variations (same root word)
            if user_clean in correct_clean or correct_clean in user_clean:
                return {
                    "is_correct": False,
                    "is_morphological_error": True,
                    "is_synonym": False,
                    "explanation": "Морфологическая ошибка - правильное значение, но неправильная форма"
                }
            
            # For now, treat everything else as incorrect
            return {
                "is_correct": False,
                "is_morphological_error": False,
                "is_synonym": False,
                "explanation": "Неправильный ответ"
            }
            
        except Exception as e:
            print(f"Error analyzing answer: {e}")
            # Fallback to simple string comparison
            is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
            return {
                "is_correct": is_correct,
                "is_morphological_error": False,
                "is_synonym": False,
                "explanation": "Проверка ответа выполнена" if is_correct else "Ответ неверный"
            }
    
    def classify_error(self, user_answer: str, correct_answer: str, 
                      target_language: str) -> str:
        """Classify the type of error made by the user"""
        try:
            # Simple error classification
            user_clean = user_answer.lower().strip()
            correct_clean = correct_answer.lower().strip()
            
            if user_clean == correct_clean:
                return "Correct: No error"
            
            # Check for spelling errors (similar words)
            if len(user_clean) == len(correct_clean):
                diff_count = sum(1 for a, b in zip(user_clean, correct_clean) if a != b)
                if diff_count <= 2:
                    return "Spelling: Letter substitution"
            
            # Check for morphological errors
            if user_clean in correct_clean or correct_clean in user_clean:
                return "Grammar: Morphological error"
            
            # Default to vocabulary error
            return "Vocabulary: Wrong word choice"
            
        except Exception as e:
            print(f"Error classifying error: {e}")
            return "Unknown: Analysis failed"
    
    def generate_multiple_choice_options(self, correct_answer: str, 
                                       target_language: str) -> List[str]:
        """Generate multiple choice options for a word"""
        try:
            # Simple fallback options for now
            fallback_options = ["different", "another", "alternative", "other", "similar"]
            return [opt for opt in fallback_options if opt != correct_answer][:2]
            
        except Exception as e:
            print(f"Error generating multiple choice options: {e}")
            return ["option1", "option2"]
    
    def get_task_type_for_word(self, progress: int) -> str:
        """Determine task type based on word progress"""
        # Find the appropriate probability distribution
        for (min_progress, max_progress), probabilities in TASK_PROBABILITIES.items():
            if min_progress <= progress <= max_progress:
                # Weighted random selection
                task_types = list(probabilities.keys())
                weights = list(probabilities.values())
                selected_type = random.choices(task_types, weights=weights)[0]
                return selected_type
        
        # Default to translation for high progress
        return "translation"

