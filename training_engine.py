"""
Training engine for managing training sessions
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import random
from database import DatabaseManager
from ai_service import AIService
from config import TRAINING_SESSION_LIMITS
from translations import (
    get_translation, get_user_language_index,
    insert_word_instruction, word_in_sentence, translate_word_to, to_language,
    choose_correct_translation_for, translation_for_word, translation_label,
    excellent_synonym, good_meaning_check_form, correct_well_done, incorrect_correct_answer,
    translate_sentence_instruction, translate_word_instruction
)



class TrainingEngine:
    """Manages training sessions and word selection"""
    
    def __init__(self, db_manager: DatabaseManager, ai_service: AIService):
        """Initialize training engine"""
        self.db = db_manager
        self.ai = ai_service
    
    def _get_user_language_index(self, user_id: str) -> int:
        """Get user's interface language index"""
        # Попробуем получить язык из сессии Streamlit, если доступно
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and st.session_state.get('user_data') and 'interface_language' in st.session_state.user_data:
                return get_user_language_index(st.session_state.user_data['interface_language'])
        except:
            pass
        
        # Fallback: получить из базы данных
        user_data = self.db.get_user_by_id(user_id)
        if user_data and 'interface_language' in user_data:
            return get_user_language_index(user_data['interface_language'])
        return 0  # Default to English
    
    def start_training_session(self, user_id: str, language: str, 
                             session_limit: int) -> Dict:
        """Start a new training session - creates only first task for fast loading"""
        # Validate session limit
        if session_limit not in TRAINING_SESSION_LIMITS:
            return {"success": False, "error": "Invalid session limit"}
        
        # Get words for training
        words = self.db.get_words_for_training(user_id, language, session_limit)
        
        if not words:
            return {"success": False, "error": "No words available for training"}
        
        # Create training session
        session_id = f"session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save session state for lazy loading
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "language": language,
            "words": words,
            "current_word_index": 0,
            "total_words": len(words),
            "created_at": datetime.now().isoformat()
        }
        
        # Store session data in database or session storage
        self._save_session_state(session_id, session_data)
        
        # Create only the first task immediately
        first_task = None
        if words:
            first_task = self._create_task_for_word(words[0], user_id, language)
        
        if not first_task:
            return {"success": False, "error": "Failed to create first task"}
        
        return {
            "success": True,
            "session_id": session_id,
            "current_task": first_task,
            "current_task_index": 0,
            "total_tasks": len(words)
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
            
            # Get user data for topics and native language
            user_data = self.db.get_user_by_id(user_id)
            preferred_topics = user_data.get("preferred_topics", []) if user_data else []
            if preferred_topics and isinstance(preferred_topics, list):
                user_preferred_topic = random.choice(preferred_topics) if preferred_topics else "general"
            else:
                user_preferred_topic = "general"
            
            # Get native language (moved outside the if block)
            native_language = user_data.get("native_language", "English") if user_data else "English"
        except Exception as e:
            return None
            
        if task_type == "translation":
            return self._create_translation_task(word, target_word, native_word, native_language, user_id, user_preferred_topic)
        
        elif task_type == "multiple_choice":
            return self._create_multiple_choice_task(word, target_word, native_word, language, native_language, user_id,user_preferred_topic)
        
        elif task_type == "fill_blank":
            return self._create_fill_blank_task(word, target_word, native_word, 
                                             preferred_topics, user_errors, language, native_language, user_id, user_preferred_topic)
        
        return None
    
    def _create_translation_task(self, word: Dict, target_word: str, native_word: str, native_language: str, user_id: str, user_preferred_topic: str) -> Dict:
        """Create a translation task where user translates from native to target language"""
        lang_idx = self._get_user_language_index(user_id)

        # Generate sentence with the target word in target language
        sentence = self.ai.generate_sentence(target_word, user_preferred_topic, [], word.get("language", ""), native_language)
        
        if sentence:
            # Translate the sentence to native language (this is what user will see)
            sentence_translation = self.ai.translate_sentence(sentence, word.get("language", ""), native_language)
            
            if sentence_translation:
                # User sees sentence in native language and translates to target language
                instruction = f"{get_translation(translate_sentence_instruction, lang_idx)} {word.get('language', '')}:"
                task_sentence = sentence_translation  # What user sees (native language)
                context_word = native_word  # Key word for context
            else:
                # Fallback if translation fails
                instruction = f"{get_translation(translate_word_instruction, lang_idx)} '{native_word}' {get_translation(to_language, lang_idx)} {word.get('language', '')}"
                task_sentence = None
                context_word = native_word
        else:
            # Fallback to simple word translation
            instruction = f"{get_translation(translate_word_instruction, lang_idx)} '{native_word}' {get_translation(to_language, lang_idx)} {word.get('language', '')}"
            task_sentence = None
            context_word = native_word

        # Prepare return data
        task_data = {
            "task_id": f"trans_{word['word_id']}",
            "word_id": word["word_id"],
            "task_type": "translation",
            "native_word": native_word,  # (what user sees - native word for context)
            "target_word": target_word,  # (correct answer - target word)
            "instruction": instruction,
            "user_input_type": "text",
            "debug_info": {
                "method": "_create_translation_task",
                "progress": word["progress"],
                "task_type": "translation"
            }
        }
        
        # Add sentence and context for user
        if task_sentence:
            task_data["sentence"] = task_sentence  # What user sees (native language)
            task_data["sentence_translation"] = context_word  # Key word for context
        else:
            # Fallback for simple word translation
            task_data["sentence"] = f"Переведите слово '{native_word}'"
            task_data["sentence_translation"] = native_word
        
        return task_data
    
    def _create_multiple_choice_task(self, word: Dict, target_word: str, 
                                   native_word: str, language: str, native_language: str, user_id: str, user_preferred_topic: str) -> Dict:
        """Create a multiple choice task with sentence context"""
        lang_idx = self._get_user_language_index(user_id)
        
        # Generate sentence with the target word (only using target_word, no native_word dependency)
        sentence = self.ai.generate_sentence(target_word, user_preferred_topic, [], language, native_language)
        if not sentence:
            # Fallback to simple word choice
            incorrect_options = self.ai.generate_multiple_choice_options(target_word, language, native_language)
            options = [target_word]  # Start with correct answer
            for option in incorrect_options:
                if option not in options and option != target_word:
                    options.append(option)
                    if len(options) >= 3:
                        break
            
            # Add fallback options if needed (generate target language options)
            if len(options) < 3:
                # Try to generate more target language options
                additional_options = self.ai.generate_multiple_choice_options(target_word, language, native_language)
                for option in additional_options:
                    if option not in options and option != target_word and len(options) < 3:
                        options.append(option)
                
            # If still not enough, add generic target language words with same part of speech
            if len(options) < 3:
                # Try to determine part of speech from the target word
                if language.lower() == "deutsch":
                    # For German adjectives (common case) - more specific options
                    generic_options = ["wichtig", "bedeutsam", "relevant", "entscheidend", "kritisch", "grundlegend", "zentral"]
                elif language.lower() == "english":
                    # For English adjectives - more specific options
                    generic_options = ["important", "significant", "relevant", "crucial", "essential", "fundamental", "central"]
                else:
                    generic_options = ["different", "another", "alternative"]
                
                for fallback in generic_options:
                    if fallback not in options and len(options) < 3:
                        options.append(fallback)
            
            random.shuffle(options)
            
            return {
                "task_id": f"mc_{word['word_id']}",
                "word_id": word["word_id"],
                "task_type": "multiple_choice",
                "native_word": native_word,  # (what user sees - native word for context)
                "target_word": target_word,  # (correct answer - target word)
                "instruction": f"{get_translation(choose_correct_translation_for, lang_idx)} {language} {get_translation(translation_for_word, lang_idx)} '{native_word}':",
                "options": options,
                "correct_index": options.index(target_word),
                "user_input_type": "select",
                "debug_info": {
                    "method": "_create_multiple_choice_task",
                    "progress": word["progress"],
                    "task_type": "multiple_choice"
                }
            }
        
        # Translate the sentence to native language
        # sentence_translation = self.ai.translate_sentence(sentence, language, native_language)
        
        # Replace target word with blank
        import re
        # Extract main word part (remove parenthetical info like "(nach D.)")
        main_word = re.split(r'\s*\(', target_word)[0].strip()
        pattern = r'\b' + re.escape(main_word) + r'\b'
        sentence_with_blank = re.sub(pattern, "_____", sentence, flags=re.IGNORECASE)
        
        # Generate incorrect options (target language words)
        incorrect_options = self.ai.generate_multiple_choice_options(target_word, language, native_language)
        
        # Create options list (all target language words) and ensure no duplicates
        options = [target_word]  # Start with correct answer
        for option in incorrect_options:
            if option not in options and option != target_word:
                options.append(option)
                if len(options) >= 3:
                    break
        
        # Add fallback options if needed (generate target language options)
        if len(options) < 3:
            # Try to generate more target language options
            additional_options = self.ai.generate_multiple_choice_options(target_word, language, native_language)
            for option in additional_options:
                if option not in options and option != target_word and len(options) < 3:
                    options.append(option)
            
            # If still not enough, add generic target language words with same part of speech
            if len(options) < 3:
                # Try to determine part of speech from the target word
                if language.lower() == "deutsch":
                    # For German adjectives (common case) - more specific options
                    generic_options = ["wichtig", "bedeutsam", "relevant", "entscheidend", "kritisch", "grundlegend", "zentral"]
                elif language.lower() == "english":
                    # For English adjectives - more specific options
                    generic_options = ["important", "significant", "relevant", "crucial", "essential", "fundamental", "central"]
                else:
                    generic_options = ["different", "another", "alternative"]
                
                for fallback in generic_options:
                    if fallback not in options and len(options) < 3:
                        options.append(fallback)
        
        random.shuffle(options)
        
        return {
            "task_id": f"mc_{word['word_id']}",
            "word_id": word["word_id"],
            "task_type": "multiple_choice",
            "native_word": native_word,  # (what user sees - native word for context)
            "target_word": target_word,  # (correct answer - target word)
            "instruction": f"{get_translation(choose_correct_translation_for, lang_idx)} {language} {get_translation(translation_for_word, lang_idx)} '{native_word}':",
            "sentence": sentence_with_blank,
            "sentence_translation": native_word,  # Only show the key word as context hint
            "options": options,
            "correct_index": options.index(target_word),
            "user_input_type": "select",
            "debug_info": {
                "method": "_create_multiple_choice_task",
                "progress": word["progress"],
                "task_type": "multiple_choice"
            }
        }
    
    def _create_fill_blank_task(self, word: Dict, target_word: str, native_word: str,
                               preferred_topics: List[str], user_errors: List[Dict], 
                               language: str, native_language: str, user_id: str, user_preferred_topic: str) -> Dict:
        """Create a fill-in-the-blank task"""
        lang_idx = self._get_user_language_index(user_id)
        # Generate sentence with the target word (only using target_word, no native_word dependency)
        sentence = self.ai.generate_sentence(target_word, user_preferred_topic, user_errors, language, native_language)
        
        if not sentence:
            # Fallback to simple translation task
            return self._create_translation_task(word, target_word, native_word, native_language, user_id, user_preferred_topic)
        
        # Translate the sentence to native language
        sentence_translation = self.ai.translate_sentence(sentence, language, native_language)
        
        # Replace target word with blank (case-insensitive)
        import re
        # Extract main word part (remove parenthetical info like "(nach D.)")
        main_word = re.split(r'\s*\(', target_word)[0].strip()
        # Use word boundaries to ensure we replace the whole word
        pattern = r'\b' + re.escape(main_word) + r'\b'
        sentence_with_blank = re.sub(pattern, "_____", sentence, flags=re.IGNORECASE)
        
        return {
            "task_id": f"fill_{word['word_id']}",
            "word_id": word["word_id"],
            "task_type": "fill_blank",
            "native_word": native_word,  # (what user sees - native word for context)
            "target_word": target_word,  # (correct answer - target word)
            "instruction": f"{get_translation(insert_word_instruction, lang_idx)} {language} {get_translation(word_in_sentence, lang_idx)}",
            "sentence": sentence_with_blank,
            "sentence_translation": native_word,  # Only show the key word as context hint
            "user_input_type": "text",
            "debug_info": {
                "method": "_create_fill_blank_task",
                "progress": word["progress"],
                "task_type": "fill_blank"
            }
        }
    
    def submit_answer(self, task_id: str, user_answer: str, 
                     user_id: str, session_id: str = None) -> Dict:
        """Process user's answer and update progress"""
        lang_idx = self._get_user_language_index(user_id)
        # Extract word_id from task_id
        word_id = task_id.split("_", 1)[1]
        
        # Get word data
        words = self.db.get_user_words(user_id)
        word = next((w for w in words if w["word_id"] == word_id), None)
        
        if not word:
            return {"success": False, "error": "Word not found"}
        
        # Get user data for native language
        user_data = self.db.get_user_by_id(user_id)
        native_language = user_data.get("native_language", "English") if user_data else "English"
        
        # Determine task type and correct answer
        task_type = task_id.split("_")[0]  # trans_, mc_, fill_
        language = word["language"]
        
        if task_type == "trans":
            # For translation tasks, user translates from native language to target language
            # So we need to analyze the user's answer in target language
            # Stage 1: Analyze the entire sentence in target language
            sentence_analysis = self.ai.analyze_translation_sentence(user_answer, language, native_language)
            
            # Stage 2: Analyze the target word usage (user should use target word)
            word_analysis = self.ai.analyze_target_word_usage(user_answer, word["target_word"], language, native_language)
            
            # Stage 3: Classify errors and determine result
            analysis = self.ai.classify_translation_errors(sentence_analysis, word_analysis)
        elif task_type == "fill":
            # For fill_blank tasks, use enhanced analysis for synonyms and alternatives
            analysis = self.ai.analyze_fill_blank_answer(user_answer, word["target_word"], language, native_language)
        else:
            # For other task types, compare with target word
            analysis = self.ai.analyze_answer(user_answer, word["target_word"], language, native_language)
        
        # Update word progress
        progress_result = self.db.update_word_progress(
            word_id=word_id,
            is_correct=analysis["is_correct"],
            is_morphological_error=analysis["is_morphological_error"],
            is_synonym=analysis["is_synonym"]
        )
        
        # Log error if answer was wrong
        if not analysis["is_correct"] and not analysis["is_morphological_error"]:
            if task_type == "trans" and "error_categories" in analysis:
                # Use detailed error logging for translation tasks
                self.db.log_translation_errors(
                    user_id, language, 
                    analysis.get("error_categories", []),
                    analysis.get("error_details", []),
                    analysis.get("sentence_quality", "unknown")
                )
            else:
                # Use simple error logging for other task types
                error_description = self.ai.classify_error(user_answer, word["target_word"], language, native_language)
                self.db.log_error(user_id, language, error_description)
        
        # Prepare response with translated messages
        if analysis["is_correct"]:
            message = f"✅ {get_translation(correct_well_done, lang_idx)}"
        elif analysis["is_morphological_error"]:
            message = f"⚠️ {get_translation(good_meaning_check_form, lang_idx)}"
        elif analysis["is_synonym"]:
            message = f"ℹ️ {get_translation(excellent_synonym, lang_idx)} '{word["target_word"]}'."
        else:
            message = f"❌ {get_translation(incorrect_correct_answer, lang_idx)} '{word["target_word"]}'."
        
        
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
        
        # Add detailed error information for translation tasks
        if task_type == "trans" and "error_categories" in analysis:
            response["error_categories"] = analysis.get("error_categories", [])
            response["error_details"] = analysis.get("error_details", [])
            response["sentence_quality"] = analysis.get("sentence_quality", "unknown")
            response["sentence_analysis"] = analysis.get("sentence_analysis", {})
            response["word_analysis"] = analysis.get("word_analysis", {})
        # Multilingual messages using get_translation and lang_idx
        
        if analysis["is_synonym"]:
            response["message"] = f"ℹ️ {get_translation(excellent_synonym, lang_idx)} '{word["target_word"]}'."
        elif analysis["is_morphological_error"]:
            response["message"] = f"⚠️ {get_translation(good_meaning_check_form, lang_idx)}"
        elif analysis["is_correct"]:
            response["message"] = f"✅ {get_translation(correct_well_done, lang_idx)}"
        else:
            response["message"] = f"❌ {get_translation(incorrect_correct_answer, lang_idx)} '{word["target_word"]}'."

        # Note: Next task creation is now handled in background during task display
        # No need to create it here as it's already prepared while user was thinking

        return response
    
    def _save_session_state(self, session_id: str, session_data: Dict) -> None:
        """Save session state for lazy loading"""
        try:
            import streamlit as st
            # Use Streamlit session state for temporary storage
            if not hasattr(st.session_state, 'training_sessions'):
                st.session_state.training_sessions = {}
            st.session_state.training_sessions[session_id] = session_data
        except:
            # Fallback: could store in database if needed
            pass
    
    def _get_session_state(self, session_id: str) -> Optional[Dict]:
        """Get session state for lazy loading"""
        try:
            import streamlit as st
            if hasattr(st.session_state, 'training_sessions'):
                return st.session_state.training_sessions.get(session_id)
        except:
            pass
        return None
    
    def get_next_task(self, session_id: str) -> Dict:
        """Get the next task in the training session"""
        session_data = self._get_session_state(session_id)
        
        if not session_data:
            return {"success": False, "error": "Session not found"}
        
        current_index = session_data["current_word_index"]
        words = session_data["words"]
        user_id = session_data["user_id"]
        language = session_data["language"]
        
        # Check if we have more tasks
        if current_index >= len(words):
            return {"success": False, "error": "No more tasks available"}
        
        # Update session state FIRST - increment the index
        session_data["current_word_index"] = current_index + 1
        self._save_session_state(session_id, session_data)
        
        # Check if we have a pre-generated task
        if hasattr(session_data, 'pre_generated_task') and session_data.get('pre_generated_task'):
            next_task = session_data['pre_generated_task']
            # Clear the pre-generated task
            session_data['pre_generated_task'] = None
        else:
            # Get the next word and create task
            next_word = words[current_index]
            next_task = self._create_task_for_word(next_word, user_id, language)
        
        if not next_task:
            return {"success": False, "error": "Failed to create next task"}
        
        # Create next task in background for smooth experience
        self._create_next_task_in_background(session_id, session_data, current_index + 1, words, user_id, language)
        
        return {
            "success": True,
            "current_task": next_task,
            "current_task_index": current_index + 1,  # Return the updated index
            "total_tasks": len(words),
            "is_last_task": current_index + 1 >= len(words)
        }
    
    def _create_next_task_in_background(self, session_id: str, session_data: Dict, 
                                      next_index: int, words: List[Dict], 
                                      user_id: str, language: str) -> None:
        """Create next task in background for smooth user experience"""
        try:
            # Check if we have more tasks and no pre-generated task exists
            if (next_index < len(words) and 
                not session_data.get('pre_generated_task')):
                
                # Get the next word
                next_word = words[next_index]
                
                # Create task in background
                next_task = self._create_task_for_word(next_word, user_id, language)
                
                if next_task:
                    # Store pre-generated task
                    session_data['pre_generated_task'] = next_task
                    self._save_session_state(session_id, session_data)
                    
        except Exception as e:
            # Don't fail the main flow if background task fails
            pass
    
    def prepare_next_task_in_background(self, session_id: str) -> None:
        """Prepare next task in background while user is thinking"""
        try:
            session_data = self._get_session_state(session_id)
            if not session_data:
                return
            
            current_index = session_data["current_word_index"]
            words = session_data["words"]
            user_id = session_data["user_id"]
            language = session_data["language"]
            
            # Check if we have more tasks and no pre-generated task exists
            if (current_index < len(words) and 
                not session_data.get('pre_generated_task')):
                
                # Get the current word (next task to prepare)
                next_word = words[current_index]
                
                # Create task in background
                next_task = self._create_task_for_word(next_word, user_id, language)
                
                if next_task:
                    # Store pre-generated task
                    session_data['pre_generated_task'] = next_task
                    self._save_session_state(session_id, session_data)
                    
        except Exception as e:
            # Don't fail the main flow if background task fails
            pass
    
    def get_current_task_info(self, session_id: str) -> Dict:
        """Get information about current task without creating it"""
        session_data = self._get_session_state(session_id)
        
        if not session_data:
            return {"success": False, "error": "Session not found"}
        
        current_index = session_data["current_word_index"]
        total_tasks = session_data["total_words"]
        
        return {
            "success": True,
            "current_task_index": current_index,
            "total_tasks": total_tasks,
            "is_last_task": current_index >= total_tasks
        }
