"""
Database connection and operations for Lasty Language Smart Trainer
"""
import uuid
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
import bcrypt
import httpx

class DatabaseManager:
    """Manages all database operations for the application"""
    
    def __init__(self):
        """Initialize Supabase client"""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase URL and Key must be provided")
        
        try:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            raise e
    
    def _execute_with_retry(self, operation, max_retries=3, delay=1.0):
        """Execute database operation with retry logic"""
        for attempt in range(max_retries):
            try:
                return operation()
            except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Database operation failed after {max_retries} attempts: {str(e)}")
                print(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(delay * (attempt + 1))  # Exponential backoff
            except Exception as e:
                # For non-network errors, don't retry
                raise e
    
    # User Management Methods
    def create_user(self, login: str, password: str, native_language: str, 
                   learning_languages: List[str], preferred_topics: List[str], 
                   interface_language: str = None) -> str:
        """Create a new user account"""
        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user_data = {
            "user_id": user_id,
            "login": login,
            "password_hash": password_hash,
            "native_language": native_language,
            "learning_languages": learning_languages,
            "preferred_topics": preferred_topics,
            "interface_language": interface_language or native_language,
            "is_admin": False
        }
        
        try:
            result = self.supabase.table("users").insert(user_data).execute()
            return user_id
        except Exception as e:
            # If RLS is blocking, try with service role key
            print(f"RLS error: {e}")
            raise Exception("Registration failed due to security policy. Please contact administrator.")
    
    def authenticate_user(self, login: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data if successful"""
        def operation():
            return self.supabase.table("users").select("*").eq("login", login).execute()
        
        result = self._execute_with_retry(operation)
        
        if not result.data:
            return None
        
        user = result.data[0]
        if bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
            # Remove password hash from returned data
            user.pop("password_hash", None)
            return user
        
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user data by user ID"""
        def operation():
            return self.supabase.table("users").select("*").eq("user_id", user_id).execute()
        
        result = self._execute_with_retry(operation)
        return result.data[0] if result.data else None
    
    # Word Management Methods
    def import_word_pairs(self, user_id: str, word_pairs: List[Tuple[str, str]], 
                         target_language: str) -> Dict:
        """Import word pairs for a user"""
        imported_count = 0
        duplicate_count = 0
        error_pairs = []
        
        for native_word, target_word in word_pairs:
            # Check for duplicates (case-insensitive)
            existing = self.supabase.table("word_pairs").select("word_id").eq(
                "user_id", user_id
            ).eq("language", target_language).execute()
            
            # Check if word pair already exists (case-insensitive)
            is_duplicate = False
            for existing_word in existing.data:
                if (existing_word.get("native_word", "").lower() == native_word.strip().lower() and
                    existing_word.get("target_word", "").lower() == target_word.strip().lower()):
                    is_duplicate = True
                    break
            
            if is_duplicate:
                duplicate_count += 1
                continue
            
            # Create new word pair
            word_data = {
                "word_id": str(uuid.uuid4()),
                "user_id": user_id,
                "native_word": native_word.strip(),
                "target_word": target_word.strip(),
                "progress": 0,
                "last_training_date": None,
                "next_training_date": datetime.now().date().isoformat(),
                "language": target_language
            }
            
            try:
                result = self.supabase.table("word_pairs").insert(word_data).execute()
                if result.data:
                    imported_count += 1
                else:
                    error_pairs.append((native_word, target_word, "No data returned from insert"))
            except Exception as e:
                print(f"Error inserting word pair: {native_word} -> {target_word}")
                print(f"Error details: {e}")
                print(f"Word data: {word_data}")
                error_pairs.append((native_word, target_word, str(e)))
        
        return {
            "imported": imported_count,
            "duplicates": duplicate_count,
            "errors": error_pairs
        }
    
    def get_user_words(self, user_id: str, language: str = None) -> List[Dict]:
        """Get all word pairs for a user"""
        query = self.supabase.table("word_pairs").select("*").eq("user_id", user_id)
        
        if language:
            query = query.eq("language", language)
        
        result = query.execute()
        return result.data
    
    def delete_word(self, word_id: str, user_id: str) -> bool:
        """Delete a word pair"""
        result = self.supabase.table("word_pairs").delete().eq(
            "word_id", word_id
        ).eq("user_id", user_id).execute()
        
        return len(result.data) > 0
    
    # Training Methods
    def get_words_for_training(self, user_id: str, language: str, limit: int) -> List[Dict]:
        """Get words for training session based on algorithm"""
        today = datetime.now().date()
        
        # Priority 1: Words with past due training date
        def get_overdue_words():
            return self.supabase.table("word_pairs").select("*").eq(
                "user_id", user_id
            ).eq("language", language).lte("next_training_date", today).execute()
        
        overdue_words = self._execute_with_retry(get_overdue_words)
        
        if overdue_words.data:
            # If we have enough overdue words, return random selection
            if len(overdue_words.data) >= limit:
                import random
                return random.sample(overdue_words.data, limit)
            else:
                # Use all overdue words and fill with random others
                remaining_limit = limit - len(overdue_words.data)
                
                def get_other_words():
                    return self.supabase.table("word_pairs").select("*").eq(
                        "user_id", user_id
                    ).eq("language", language).neq("next_training_date", today).execute()
                
                other_words = self._execute_with_retry(get_other_words)
                
                if other_words.data:
                    import random
                    additional_words = random.sample(
                        other_words.data, 
                        min(remaining_limit, len(other_words.data))
                    )
                    return overdue_words.data + additional_words
                else:
                    return overdue_words.data
        
        # Priority 3: Any words if no overdue words
        def get_all_words():
            return self.supabase.table("word_pairs").select("*").eq(
                "user_id", user_id
            ).eq("language", language).execute()
        
        all_words = self._execute_with_retry(get_all_words)
        
        if all_words.data:
            import random
            return random.sample(all_words.data, min(limit, len(all_words.data)))
        
        return []
    
    def update_word_progress(self, word_id: str, is_correct: bool, 
                           is_morphological_error: bool = False, 
                           is_synonym: bool = False) -> Dict:
        """Update word progress based on training result"""
        from config import PROGRESS_INCREMENT, PROGRESS_DECREMENT, EBINGHAUS_INTERVALS
        
        # Get current word data
        result = self.supabase.table("word_pairs").select("*").eq("word_id", word_id).execute()
        if not result.data:
            return {"success": False, "error": "Word not found"}
        
        word = result.data[0]
        current_progress = word["progress"]
        today = datetime.now().date()
        
        # Calculate new progress
        if is_morphological_error:
            # Progress remains unchanged
            new_progress = current_progress
            # Keep existing next_training_date (convert from string if needed)
            existing_date = word["next_training_date"]
            if isinstance(existing_date, str):
                new_next_date = datetime.fromisoformat(existing_date).date()
            else:
                new_next_date = existing_date
        elif is_synonym:
            # Progress remains unchanged, but answer is accepted
            new_progress = current_progress
            # Keep existing next_training_date (convert from string if needed)
            existing_date = word["next_training_date"]
            if isinstance(existing_date, str):
                new_next_date = datetime.fromisoformat(existing_date).date()
            else:
                new_next_date = existing_date
        elif is_correct:
            # Increase progress
            new_progress = min(100, current_progress + PROGRESS_INCREMENT)
            # Calculate new next training date
            interval_days = 1  # Default
            for (min_progress, max_progress), days in EBINGHAUS_INTERVALS.items():
                if min_progress <= new_progress <= max_progress:
                    interval_days = days
                    break
            new_next_date = today + timedelta(days=interval_days)
        else:
            # Decrease progress and repeat today
            new_progress = max(0, current_progress - PROGRESS_DECREMENT)
            new_next_date = today
        
        # Update database
        update_data = {
            "progress": new_progress,
            "last_training_date": today.isoformat(),
            "next_training_date": new_next_date.isoformat()
        }
        
        self.supabase.table("word_pairs").update(update_data).eq("word_id", word_id).execute()
        
        return {
            "success": True,
            "new_progress": new_progress,
            "next_training_date": new_next_date
        }
    
    # Error Tracking Methods
    def log_error(self, user_id: str, language: str, error_description: str) -> None:
        """Log or update user error"""
        # Check if error already exists
        existing = self.supabase.table("errors").select("*").eq(
            "user_id", user_id
        ).eq("language", language).eq("description", error_description).execute()
        
        if existing.data:
            # Increment count
            current_count = existing.data[0]["count"]
            self.supabase.table("errors").update({
                "count": current_count + 1
            }).eq("error_id", existing.data[0]["error_id"]).execute()
        else:
            # Create new error record
            error_data = {
                "error_id": str(uuid.uuid4()),
                "user_id": user_id,
                "language": language,
                "description": error_description,
                "count": 1
            }
            self.supabase.table("errors").insert(error_data).execute()
    
    def log_translation_errors(self, user_id: str, language: str, error_categories: List[str], 
                             error_details: List[str], sentence_quality: str) -> None:
        """Log detailed translation errors with categories"""
        for i, (category, detail) in enumerate(zip(error_categories, error_details)):
            # Include sentence quality in the description since we don't have separate columns
            error_description = f"{category}: {detail} (Quality: {sentence_quality})"
            
            # Check if error already exists
            existing = self.supabase.table("errors").select("*").eq(
                "user_id", user_id
            ).eq("language", language).eq("description", error_description).execute()
            
            if existing.data:
                # Increment count
                current_count = existing.data[0]["count"]
                self.supabase.table("errors").update({
                    "count": current_count + 1
                }).eq("error_id", existing.data[0]["error_id"]).execute()
            else:
                # Create new error record (using only existing columns)
                error_data = {
                    "error_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "language": language,
                    "description": error_description,
                    "count": 1
                }
                self.supabase.table("errors").insert(error_data).execute()
    
    def get_user_errors(self, user_id: str, language: str = None) -> List[Dict]:
        """Get user error statistics"""
        query = self.supabase.table("errors").select("*").eq("user_id", user_id)
        
        if language:
            query = query.eq("language", language)
        
        result = query.order("count", desc=True).execute()
        return result.data
    
    # Statistics Methods
    def get_user_statistics(self, user_id: str, language: str = None) -> Dict:
        """Get user training statistics"""
        # Get word counts by progress level
        words_query = self.supabase.table("word_pairs").select("*").eq("user_id", user_id)
        if language:
            words_query = words_query.eq("language", language)
        
        words_result = words_query.execute()
        words = words_result.data
        
        if not words:
            return {
                "total_words": 0, 
                "progress_distribution": {}, 
                "recent_activity": 0,
                "words_ready_for_training": 0
            }
        
        # Calculate progress distribution
        progress_distribution = {}
        for word in words:
            progress = word["progress"]
            if progress < 20:
                level = "0"
            elif progress < 40:
                level = "20"
            elif progress < 60:
                level = "40"
            elif progress < 80:
                level = "60"
            elif progress < 100:
                level = "80"
            else:
                level = "100"
            
            progress_distribution[level] = progress_distribution.get(level, 0) + 1
        
        # Get recent training activity (last 7 days)
        week_ago = datetime.now().date() - timedelta(days=7)
        recent_words = [w for w in words if w["last_training_date"] and 
                       datetime.strptime(w["last_training_date"], "%Y-%m-%d").date() >= week_ago]
        
        return {
            "total_words": len(words),
            "progress_distribution": progress_distribution,
            "recent_activity": len(recent_words),
            "words_ready_for_training": len([w for w in words if 
                w["next_training_date"] and 
                datetime.strptime(w["next_training_date"], "%Y-%m-%d").date() <= datetime.now().date()])
        }
    
    def update_user_languages(self, user_id: str, learning_languages: List[str]) -> bool:
        """Update user's learning languages"""
        try:
            result = self.supabase.table("users").update({
                "learning_languages": learning_languages
            }).eq("user_id", user_id).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error updating user languages: {e}")
            return False
    
    def update_user_topics(self, user_id: str, preferred_topics: List[str]) -> bool:
        """Update user's preferred topics"""
        try:
            result = self.supabase.table("users").update({
                "preferred_topics": preferred_topics
            }).eq("user_id", user_id).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error updating user topics: {e}")
            return False
    
    def update_user_interface_language(self, user_id: str, interface_language: str) -> bool:
        """Update user's interface language"""
        try:
            result = self.supabase.table("users").update({
                "interface_language": interface_language
            }).eq("user_id", user_id).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error updating interface language: {e}")
            return False