"""
Training engine for managing training sessions
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import random
from database import DatabaseManager
from ai_service import AIService
from config import TRAINING_SESSION_LIMITS



class TrainingEngine:
    """Manages training sessions and word selection"""
    
    def __init__(self, db_manager: DatabaseManager, ai_service: AIService):
        """Initialize training engine"""
        self.db = db_manager
        self.ai = ai_service
    
    def start_training_session(self, user_id: str, language: str, 
                             session_limit: int) -> Dict:
        """Start a new training session"""
        # Validate session limit
        if session_limit not in TRAINING_SESSION_LIMITS:
            return {"success": False, "error": "Invalid session limit"}
        
        # Get words for training
        words = self.db.get_words_for_training(user_id, language, session_limit)
        
        if not words:
            return {"success": False, "error": "No words available for training"}
        
        # Create training session
        session_id = f"session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare training tasks
        tasks = []
        for word in words:
            task = self._create_task_for_word(word, user_id, language)
            if task:
                tasks.append(task)
        
        return {
            "success": True,
            "session_id": session_id,
            "tasks": tasks,
            "total_tasks": len(tasks)
        }
    
    def _create_task_for_word(self, word: Dict, user_id: str, language: str) -> Optional[Dict]:
        """Create a training task for a specific word"""
        try:
            progress = word["progress"]
            target_word = word["target_word"]
            native_word = word["native_word"]
            
            # Determine task type based on progress
            task_type = self.ai.get_task_type_for_word(progress)
            
            # Get user errors for sentence generation
            user_errors = self.db.get_user_errors(user_id, language)
            
            # Get user data for topics
            user_data = self.db.get_user_by_id(user_id)
            preferred_topics = user_data.get("preferred_topics", []) if user_data else []
        except Exception as e:
            return None
        
        if task_type == "translation":
            return self._create_translation_task(word, target_word, native_word)
        
        elif task_type == "multiple_choice":
            return self._create_multiple_choice_task(word, target_word, native_word, language)
        
        elif task_type == "fill_blank":
            return self._create_fill_blank_task(word, target_word, native_word, 
                                             preferred_topics, user_errors, language)
        
        return None
    
    def _create_translation_task(self, word: Dict, target_word: str, native_word: str) -> Dict:
        """Create a translation task with a sentence context and blank"""
        # Try generating a sentence with the target word in context (in Russian or interface/native language)
        # The sentence should contain the target word (e.g., на русском, если изучается английский)
        sentence = self.ai.generate_sentence(target_word, [], [], word.get("language", ""))
        if sentence:
            import re
            pattern = r'\b' + re.escape(target_word) + r'\b'
            sentence_with_blank = re.sub(pattern, "_____", sentence, flags=re.IGNORECASE)
            instruction = (
                f"Вставьте английский перевод пропущенного слова ('{target_word}') в следующем предложении:\n"
                f"{sentence_with_blank}"
            )
        else:
            instruction = f"Переведите '{target_word}' на английский: {sentence}"

        return {
            "task_id": f"trans_{word['word_id']}",
            "word_id": word["word_id"],
            "task_type": "translation",
            "native_word": target_word,
            "target_word": native_word,
            "instruction": instruction,
            "user_input_type": "text"
        }
    
    def _create_multiple_choice_task(self, word: Dict, target_word: str, 
                                   native_word: str, language: str) -> Dict:
        """Create a multiple choice task with sentence context"""
        # Generate sentence with the target word
        sentence = self.ai.generate_sentence(native_word, [], [], language)
        if not sentence:
            # Fallback to simple word choice
            incorrect_options = self.ai.generate_multiple_choice_options(native_word, language)
            options = [native_word]  # Start with correct answer
            for option in incorrect_options:
                if option not in options and option != native_word:
                    options.append(option)
                    if len(options) >= 3:
                        break
            
            # Add fallback options if needed
            fallback_options = ["different", "another", "alternative"]
            for fallback in fallback_options:
                if fallback not in options and len(options) < 3:
                    options.append(fallback)
            
            random.shuffle(options)
            
            return {
                "task_id": f"mc_{word['word_id']}",
                "word_id": word["word_id"],
                "task_type": "multiple_choice",
                "native_word": target_word,
                "target_word": native_word,
                "instruction": f"Выберите правильный перевод для '{target_word}':",
                "options": options,
                "correct_index": options.index(native_word),
                "user_input_type": "select"
            }
        
        # Replace target word with blank
        import re
        pattern = r'\b' + re.escape(native_word) + r'\b'
        sentence_with_blank = re.sub(pattern, "_____", sentence, flags=re.IGNORECASE)
        
        # Generate incorrect options (English words)
        incorrect_options = self.ai.generate_multiple_choice_options(native_word, "English")
        
        # Create options list (all English words) and ensure no duplicates
        options = [native_word]  # Start with correct answer
        for option in incorrect_options:
            if option not in options and option != native_word:
                options.append(option)
                if len(options) >= 3:
                    break
        
        # Add fallback options if needed
        fallback_options = ["different", "another", "alternative"]
        for fallback in fallback_options:
            if fallback not in options and len(options) < 3:
                options.append(fallback)
        
        random.shuffle(options)
        
        return {
            "task_id": f"mc_{word['word_id']}",
            "word_id": word["word_id"],
            "task_type": "multiple_choice",
            "native_word": target_word,  #  word (what user sees)
            "target_word": native_word,  #  word (correct answer)
            "instruction": f"Выберите правильный перевод для '{target_word}':",
            "sentence": sentence_with_blank,
            "sentence_translation": f"Translation: {target_word}",
            "options": options,
            "correct_index": options.index(native_word),
            "user_input_type": "select"
        }
    
    def _create_fill_blank_task(self, word: Dict, target_word: str, native_word: str,
                               preferred_topics: List[str], user_errors: List[Dict], 
                               language: str) -> Dict:
        """Create a fill-in-the-blank task"""
        # Generate sentence with the target word (English word for English sentence)
        sentence = self.ai.generate_sentence(native_word, preferred_topics, user_errors, language)
        
        if not sentence:
            # Fallback to simple translation task
            return self._create_translation_task(word, target_word, native_word)
        
        # Replace target word with blank (case-insensitive)
        import re
        # Use word boundaries to ensure we replace the whole word
        pattern = r'\b' + re.escape(native_word) + r'\b'
        sentence_with_blank = re.sub(pattern, "_____", sentence, flags=re.IGNORECASE)
        
        return {
            "task_id": f"fill_{word['word_id']}",
            "word_id": word["word_id"],
            "task_type": "fill_blank",
            "native_word": target_word,  # (what user sees - Russian word)
            "target_word": native_word,  # (correct answer - English word)
            "instruction": f"Вставьте английский перевод пропущенного слова ('{target_word}') в следующем предложении:",
            "sentence": sentence_with_blank,
            "sentence_translation": f"Перевод: {target_word}",
            "user_input_type": "text"
        }
    
    def submit_answer(self, task_id: str, user_answer: str, 
                     user_id: str) -> Dict:
        """Process user's answer and update progress"""
        # Extract word_id from task_id
        word_id = task_id.split("_", 1)[1]
        
        # Get word data
        words = self.db.get_user_words(user_id)
        word = next((w for w in words if w["word_id"] == word_id), None)
        
        if not word:
            return {"success": False, "error": "Word not found"}
        
        # Get the correct English word (what user should type)
        correct_english_word = word["native_word"]  # This is the English word
        language = word["language"]
        
        # Analyze the answer (user types English, we compare with correct English)
        analysis = self.ai.analyze_answer(user_answer, correct_english_word, "English")
        
        # Update word progress
        progress_result = self.db.update_word_progress(
            word_id=word_id,
            is_correct=analysis["is_correct"],
            is_morphological_error=analysis["is_morphological_error"],
            is_synonym=analysis["is_synonym"]
        )
        
        # Log error if answer was wrong
        if not analysis["is_correct"] and not analysis["is_morphological_error"]:
            error_description = self.ai.classify_error(user_answer, correct_english_word, "English")
            self.db.log_error(user_id, language, error_description)
        
        # Prepare response with Russian messages
        if analysis["is_correct"]:
            message = "✅ Правильно!"
        elif analysis["is_morphological_error"]:
            message = "⚠️ Почти правильно! Проверьте форму слова."
        elif analysis["is_synonym"]:
            message = "ℹ️ Хорошо! Вы использовали синоним."
        else:
            message = f"❌ Неправильно. Правильный ответ: '{correct_english_word}'."
        
        response = {
            "success": True,
            "is_correct": analysis["is_correct"],
            "is_morphological_error": analysis["is_morphological_error"],
            "is_synonym": analysis["is_synonym"],
            "message": message,
            "explanation": analysis["explanation"],
            "new_progress": progress_result.get("new_progress", word["progress"]),
            "next_training_date": progress_result.get("next_training_date")
        }
        
        # Add specific messages in Russian
        if analysis["is_synonym"]:
            response["message"] = f"Отлично! Это синоним. Мы изучаем слово '{correct_english_word}'."
        elif analysis["is_morphological_error"]:
            response["message"] = "Хороший смысл, но проверьте форму слова. Ответ принят!"
        elif analysis["is_correct"]:
            response["message"] = "Правильно! Молодец!"
        else:
            response["message"] = f"Неправильно. Правильный ответ: '{correct_english_word}'."
        
        return response
