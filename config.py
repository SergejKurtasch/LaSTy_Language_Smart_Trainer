"""
Configuration settings for Lasty Language Smart Trainer
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Application Settings
SESSION_DURATION_DAYS = 7
MAX_USERS = 50
MAX_WORDS_PER_IMPORT = 3000
IMPORT_ERROR_THRESHOLD = 0.2  # 20% error threshold

# Training Settings
TRAINING_SESSION_LIMITS = [1, 3, 5, 10, 20]
PROGRESS_INCREMENT = 20
PROGRESS_DECREMENT = 40

# Ebbinghaus Intervals (in days)
EBINGHAUS_INTERVALS = {
    (0, 19): 0,      # Initial Memorization
    (20, 39): 1,     # First Repetition
    (40, 59): 3,     # Medium Stage
    (60, 79): 7,    # Consolidation
    (80, 99): 14,    # Control Repetition
    (100, 100): 45  # Long-term Retention
}

# Task Type Probabilities by Progress Level
TASK_PROBABILITIES = {
    (0, 41): {"multiple_choice": 0.35, "fill_blank": 0.3, "translation": 0.35},
    (42, 70): {"multiple_choice": 0.2, "fill_blank": 0.3, "translation": 0.5},
    (71, 100): {"multiple_choice": 0.1, "fill_blank": 0.3, "translation": 0.6}
}

# Supported Languages
SUPPORTED_LANGUAGES = {
    "English": "en",
    "Deutsch": "de", 
    "Español": "es",
    "Russian": "ru",
    "Ukrainian": "ua",
    "Italian": "it"
}

# Interface Languages (for UI translations)
INTERFACE_LANGUAGES = {
    "English": 0,
    "Deutsch": 1, 
    "Russian": 2,
    "Español": 3,
    "Ukrainian": 4,
    "Italian": 5
}

# Preferred Topics
PREFERRED_TOPICS = ["Business", "Travel", "Hobbies", "IT", "Books", "Movies", "Music", "Games", "Sports", "Art", "Science", "History", "Geography", "Philosophy", "Religion", "Culture", "Language", "Literature", "Math", "Physics", "Chemistry", "Biology", "Computer Science", "Economics", "Law", "Medicine", "Engineering", "Architecture", "Design", "Fashion", "Food", "Drink", "Health", "Fitness", "Beauty", "Fashion", "Art", "Science", "History", "Geography", "Philosophy", "Religion", "Culture", "Language", "Literature", "Math", "Physics", "Chemistry", "Biology", "Computer Science", "Economics", "Law", "Medicine", "Engineering", "Architecture", "Design", "Fashion", "Food", "Drink", "Health", "Fitness", "Beauty"]

