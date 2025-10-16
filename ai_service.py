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
import re
import logging

class AIService:
    """Handles AI operations for sentence generation and error analysis"""
    
    def __init__(self):
        """Initialize LangChain ChatOpenAI client"""
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key must be provided")

        try:
            # Use GPT-5 family of models with supported LangChain class.
            # Even for new models (gpt-5-mini/gpt-5), use ChatOpenAI in latest langchain_openai, not ChatOpenAIVision.
            self.llm = ChatOpenAI(
                api_key=OPENAI_API_KEY,
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=100
            )
            
            self.llm_advanced = ChatOpenAI(
                api_key=OPENAI_API_KEY,
                model="gpt-4",
                temperature=0.2,
                max_tokens=200
            )
        except Exception as e:
            raise e
    
# ----------------------------- Sentence Generation -----------------------------

    def generate_sentence(self, target_word: str, user_preferred_topic: str, 
                         user_errors: List[Dict], target_language: str, 
                         native_language: str = None, native_word: str = None) -> Optional[str]:
        """Generate a sentence containing the target word using LangChain"""
        try:
            # Create topics string
            topics_str = user_preferred_topic if user_preferred_topic else "general topics"
            
            # Extract main word part (remove parenthetical info like "(nach D.)")
            import re
            main_word = re.split(r'\s*\(', target_word)[0].strip()
            
            # Enhanced prompt for sentence generation based only on target_word
            prompt = f"""
Generate a natural and varied sentence in {target_language} that:
1. Contains the word "{main_word}" in its natural grammatical form.
2. If "{main_word}" includes any language-specific particles, articles, or infinitive markers 
   (e.g., "to" in English, "zu" in German, "le/la" in French, "el/la" in Spanish, etc.),
   use only the core word (the main lexical form) in the sentence.
3. Use "{main_word}" (or its cleaned form) in the most appropriate grammatical form for the context.
4. If it's a verb, vary its tense (present, past, future, etc.) across different examples.
5. If it's a noun or adjective, vary its grammatical case, number, or gender when applicable.
6. Relate the sentence to one of these topics: {topics_str}.
7. Ensure the sentence is appropriate for language learning — natural, clear, and not overly complex.
8. Keep it grammatically correct and authentic for {target_language}.
9. Make the context meaningful enough to help the learner understand the word’s use.
10. Vary sentence structure and tone — use affirmative, negative, or interrogative forms when possible.
11. Avoid repetitive sentence patterns between generations.
12. Use only natural and common words suitable for learners.

Return only one sentence, nothing else.
"""


            # Generate response using LangChain with retry logic
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    response = self.llm.invoke(prompt)
                    result = response.content.strip()
                except Exception as e:
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        return None
                
                # Clean up the result
                if result:
                    # Remove any quotes or extra formatting
                    result = result.strip('"').strip("'").strip()
                    
                    # Basic validation - check if target word is in the sentence
                    # Extract main word part (remove parenthetical info like "(nach D.)")
                    import re
                    main_word = re.split(r'\s*\(', target_word)[0].strip()
                    
                    if main_word.lower() in result.lower():
                        return result
                    else:
                        print(f"Warning: Target word '{target_word}' (main part: '{main_word}') not found in generated sentence: '{result}'")
                        if attempt < max_attempts - 1:
                            print(f"Retrying... (attempt {attempt + 2}/{max_attempts})")
                            continue
                
                if attempt < max_attempts - 1:
                    print(f"Empty result, retrying... (attempt {attempt + 2}/{max_attempts})")
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error generating sentence: {e}")
            return None
    

    # ----------------------------- Translation -----------------------------
    def translate_sentence(self, sentence: str, target_language: str, native_language: str) -> Optional[str]:
        """Translate a sentence from target language to native language"""
        try:
            prompt = f"""Translate the following sentence from {target_language} to {native_language}:
"{sentence}"

Requirements:
1. Provide a natural, fluent translation
2. Maintain the original meaning and context
3. Use appropriate {native_language} grammar and vocabulary
4. Keep the translation clear and understandable
5. The translation should be suitable for language learning exercises
6. Avoid overly complex or idiomatic expressions
7. Make sure the translation is grammatically correct
8. Preserve the educational value of the original sentence

Return only the translation, nothing else."""

            response = self.llm.invoke(prompt)
            result = response.content.strip()
            
            if result:
                # Clean up the result
                result = result.strip('"').strip("'").strip()
                return result
            
            return None
            
        except Exception as e:
            print(f"Error translating sentence: {e}")
            return None


    # ----------------------------- Answer Analysis -----------------------------

    def analyze_answer(self, user_answer: str, correct_answer: str, 
                       target_language: str, native_language: str = None, lang_idx: int = 0) -> Dict:
        """Analyze user's answer and determine if it's correct, morphological error, or synonym.
           Enhanced for both word and sentence analysis.
        """
        try:
            # Import get_translation only when needed to prevent circular imports
            from translations import get_translation

            user_clean = user_answer.lower().strip()
            correct_clean = correct_answer.lower().strip()

            # Exact match
            if user_clean == correct_clean:
                return {
                    "is_correct": True,
                    "is_morphological_error": False,
                    "is_synonym": False,
                    "explanation": "Правильный ответ!"
                }

            # For sentence analysis, use AI to check semantic similarity
            if len(user_clean.split()) > 1 and len(correct_clean.split()) > 1:
                return self._analyze_sentence_similarity(user_answer, correct_answer, target_language, native_language)
            
            # For single words, check morphological variations
            if user_clean in correct_clean or correct_clean in user_clean:
                return {
                    "is_correct": False,
                    "is_morphological_error": True,
                    "is_synonym": False,
                    "explanation": "Хороший смысл, но проверьте форму слова. Ответ принят!"
                }

            # Default to incorrect
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
    
    def _analyze_sentence_similarity(self, user_answer: str, correct_answer: str, 
                                   target_language: str, native_language: str) -> Dict:
        """Analyze semantic similarity between user's sentence and correct sentence"""
        try:
            prompt = f"""Analyze if these two sentences in {target_language} have the same meaning:

User answer: "{user_answer}"
Correct answer: "{correct_answer}"

Rate the similarity on a scale of 1-10 where:
- 10 = Identical meaning (exact or very close translation)
- 8-9 = Very similar meaning with minor differences
- 6-7 = Similar meaning but some differences
- 4-5 = Partially similar meaning
- 1-3 = Different meaning

Respond with only a number from 1-10."""

            response = self.llm.invoke(prompt)
            similarity_score = int(response.content.strip())
            
            if similarity_score >= 9:
                return {
                    "is_correct": True,
                    "is_morphological_error": False,
                    "is_synonym": False,
                    "explanation": "Правильный ответ!"
                }
            elif similarity_score >= 7:
                return {
                    "is_correct": False,
                    "is_morphological_error": True,
                    "is_synonym": False,
                    "explanation": "Хороший смысл, но проверьте форму слова. Ответ принят!"
                }
            else:
                return {
                    "is_correct": False,
                    "is_morphological_error": False,
                    "is_synonym": False,
                    "explanation": "Неправильный ответ"
                }
                
        except Exception as e:
            print(f"Error in sentence similarity analysis: {e}")
            # Fallback to simple comparison
            return {
                "is_correct": False,
                "is_morphological_error": False,
                "is_synonym": False,
                "explanation": "Ошибка анализа ответа"
            }
    
    def classify_error(self, user_answer: str, correct_answer: str, 
                      target_language: str, native_language: str = None) -> str:
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
    
    
    # ----------------------------- Multiple Choice Options -----------------------------

    def generate_multiple_choice_options(self, correct_answer: str, 
                                       target_language: str, native_language: str = None) -> List[str]:
        """Generate multiple choice options for a word"""
        try:
            # Generate options in target language with STRICT part of speech matching
            prompt = f"""
Generate exactly 2 incorrect answer options in {target_language} for the correct answer "{correct_answer}".
Rules:

1. Both generated words MUST have the EXACT SAME part of speech as "{correct_answer}".
   - If "{correct_answer}" is an adjective → generate only adjectives.
   - If "{correct_answer}" is a verb → generate only verbs.
   - If "{correct_answer}" is a noun → generate only nouns.
   - If "{correct_answer}" is an adverb → generate only adverbs.

2. The first incorrect option must have an OPPOSITE or CONTRASTING meaning to "{correct_answer}" (an antonym or near-antonym).
3. The second incorrect option must be NEUTRAL — not similar in meaning and not opposite in meaning to "{correct_answer}".
   It should be semantically unrelated but grammatically appropriate in the same context.

4. Avoid synonyms or words with too close a meaning.
5. All words must be common, natural, and appropriate for language learning.
6. Return only the two words separated by commas — nothing else.

Example format:
<word1>, <word2>
"""


            response = self.llm.invoke(prompt)
            result = response.content.strip()
            
            if result:
                # Parse the response
                options = [opt.strip() for opt in result.split(',') if opt.strip() and opt.strip() != correct_answer]
                return options[:2]  # Return max 2 options
            
            # Fallback to language-specific options with same part of speech
            if target_language.lower() == "deutsch":
                # For adjectives (like "wesentlich")
                fallback_options = ["wichtig", "bedeutsam", "relevant", "entscheidend", "kritisch"]
            elif target_language.lower() == "english":
                fallback_options = ["important", "significant", "relevant", "crucial", "essential"]
            else:
                fallback_options = ["different", "another", "alternative"]
            
            return [opt for opt in fallback_options if opt != correct_answer][:2]
            
        except Exception as e:
            print(f"Error generating multiple choice options: {e}")
            # Language-specific fallback with same part of speech
            if target_language.lower() == "deutsch":
                return ["wichtig", "bedeutsam"]
            else:
                return ["important", "significant"]
    
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

    # ----------------------------- Word Cleaning and Language Detection -----------------------------
    
    def clean_word(self, word: str) -> str:
        """Очистить слово от пунктуации, комментариев и привести к нижнему регистру"""
        if not word or not isinstance(word, str):
            return ""
        
        # Удалить комментарии после запятых, точек с запятой и других разделителей
        word = re.split(r"[,;:.!?()]", word)[0]
        
        # Удалить все знаки пунктуации и спецсимволы, оставить только буквы и пробелы
        word = re.sub(r"[^a-zA-Zа-яА-ЯёЁ\s]", " ", word)
        
        # Удалить лишние пробелы и привести к нижнему регистру
        word = " ".join(word.split()).lower().strip()
        
        return word
    
    def clean_word_list(self, words: List[str]) -> List[str]:
        """Очистить список слов"""
        cleaned_words = []
        for word in words:
            cleaned = self.clean_word(word)
            if cleaned:  # Добавляем только непустые слова
                cleaned_words.append(cleaned)
        return cleaned_words
    
    def detect_language(self, words: List[str], language_name: str) -> bool:
        """Определить, принадлежат ли слова указанному языку"""
        try:
            if not words:
                return False
            
            # Ограничиваем количество слов для анализа
            sample_words = words[:10] if len(words) > 10 else words
            words_str = ", ".join(sample_words)
            
            prompt = f"""Определи, принадлежат ли следующие слова языку {language_name}? 
Ответь только "Да" или "Нет".
Слова: {words_str}"""
            
            response = self.llm.invoke(prompt)
            result = response.content.strip().lower()
            
            logging.info(f"Language detection for {language_name}: {words_str} -> {result}")
            
            return result in ["да", "yes", "true", "1"]
            
        except Exception as e:
            logging.error(f"Error detecting language {language_name}: {e}")
            return False
    
    def auto_detect_column_languages(self, left_column: List[str], right_column: List[str], 
                                   target_language: str, native_language: str) -> Dict:
        """Автоматически определить, какая колонка содержит target/native язык"""
        try:
            # Очищаем слова
            left_cleaned = self.clean_word_list(left_column)
            right_cleaned = self.clean_word_list(right_column)
            
            logging.info(f"Cleaned left column: {left_cleaned[:5]}...")
            logging.info(f"Cleaned right column: {right_cleaned[:5]}...")
            
            # Определяем языки для каждой колонки
            left_is_target = self.detect_language(left_cleaned, target_language)
            left_is_native = self.detect_language(left_cleaned, native_language)
            right_is_target = self.detect_language(right_cleaned, target_language)
            right_is_native = self.detect_language(right_cleaned, native_language)
            
            logging.info(f"Detection results - Left: target={left_is_target}, native={left_is_native}")
            logging.info(f"Detection results - Right: target={right_is_target}, native={right_is_native}")
            
            # Логика принятия решения
            if left_is_target and right_is_native:
                return {
                    "success": True,
                    "target_column": "left",
                    "native_column": "right",
                    "target_words": left_cleaned,
                    "native_words": right_cleaned
                }
            elif right_is_target and left_is_native:
                return {
                    "success": True,
                    "target_column": "right", 
                    "native_column": "left",
                    "target_words": right_cleaned,
                    "native_words": left_cleaned
                }
            else:
                return {
                    "success": False,
                    "error": "Не удалось определить языки колонок автоматически"
                }
                
        except Exception as e:
            logging.error(f"Error in auto_detect_column_languages: {e}")
            return {
                "success": False,
                "error": f"Ошибка при определении языков: {str(e)}"
            }

    # ----------------------------- Enhanced Translation Analysis -----------------------------
    
    def analyze_translation_sentence(self, user_sentence: str, target_language: str, 
                                   native_language: str) -> Dict:
        """Этап 1: Проверка всего предложения на корректность (грамматика, пунктуация, лексика, стиль)"""
        try:
            prompt = f"""Proofread the following sentence in {target_language}. Check its correctness and point out any inaccuracies, grammatical or stylistic mistakes, and suggest the correct version of the sentence.

Sentence: "{user_sentence}"

Requirements:
1. Check grammar, punctuation, vocabulary, and style
2. Identify any errors or issues
3. Provide a corrected version if needed
4. Be specific about what was wrong

Respond in JSON format:
{{
    "has_errors": true/false,
    "errors": ["list of specific errors found"],
    "corrected_sentence": "corrected version if needed",
    "overall_quality": "excellent/good/fair/poor"
}}"""

            response = self.llm_advanced.invoke(prompt)
            result = response.content.strip()
            
            # Try to parse JSON response
            try:
                import json
                analysis = json.loads(result)
                return {
                    "success": True,
                    "has_errors": analysis.get("has_errors", False),
                    "errors": analysis.get("errors", []),
                    "corrected_sentence": analysis.get("corrected_sentence", user_sentence),
                    "overall_quality": analysis.get("overall_quality", "fair")
                }
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "success": True,
                    "has_errors": "error" in result.lower() or "incorrect" in result.lower(),
                    "errors": ["Analysis completed but format unclear"],
                    "corrected_sentence": user_sentence,
                    "overall_quality": "fair"
                }
                
        except Exception as e:
            print(f"Error analyzing translation sentence: {e}")
            return {
                "success": False,
                "has_errors": False,
                "errors": [],
                "corrected_sentence": user_sentence,
                "overall_quality": "unknown"
            }
    
    def analyze_target_word_usage(self, user_sentence: str, target_word: str, 
                                 target_language: str, native_language: str) -> Dict:
        """Этап 2: Проверка ключевого изучаемого слова в контексте предложения"""
        try:
            prompt = f"""Analyze whether the word "{target_word}" is correctly used in the following sentence in {target_language}: "{user_sentence}"

Check:
1. Is the word present in the sentence?
2. Is it spelled correctly?
3. Is it used in the correct grammatical form?
4. Is it used in the appropriate context?
5. Does it make sense semantically?

Respond in JSON format:
{{
    "word_present": true/false,
    "spelling_correct": true/false,
    "grammar_correct": true/false,
    "context_appropriate": true/false,
    "overall_correct": true/false,
    "errors": ["list of specific issues with the word"],
    "suggested_correction": "correct form if needed"
}}"""

            response = self.llm_advanced.invoke(prompt)
            result = response.content.strip()
            
            # Try to parse JSON response
            try:
                import json
                analysis = json.loads(result)
                return {
                    "success": True,
                    "word_present": analysis.get("word_present", False),
                    "spelling_correct": analysis.get("spelling_correct", False),
                    "grammar_correct": analysis.get("grammar_correct", False),
                    "context_appropriate": analysis.get("context_appropriate", False),
                    "overall_correct": analysis.get("overall_correct", False),
                    "errors": analysis.get("errors", []),
                    "suggested_correction": analysis.get("suggested_correction", target_word)
                }
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "success": True,
                    "word_present": target_word.lower() in user_sentence.lower(),
                    "spelling_correct": True,  # Assume correct if we can't analyze
                    "grammar_correct": True,
                    "context_appropriate": True,
                    "overall_correct": target_word.lower() in user_sentence.lower(),
                    "errors": ["Analysis completed but format unclear"],
                    "suggested_correction": target_word
                }
                
        except Exception as e:
            print(f"Error analyzing target word usage: {e}")
            return {
                "success": False,
                "word_present": target_word.lower() in user_sentence.lower(),
                "spelling_correct": False,
                "grammar_correct": False,
                "context_appropriate": False,
                "overall_correct": False,
                "errors": ["Analysis failed"],
                "suggested_correction": target_word
            }
    
    def classify_translation_errors(self, sentence_analysis: Dict, word_analysis: Dict) -> Dict:
        """Этап 3: Формирование категорий ошибок на основе анализа предложения и слова"""
        try:
            error_categories = []
            error_details = []
            
            # Анализ ошибок предложения
            if sentence_analysis.get("has_errors", False):
                sentence_errors = sentence_analysis.get("errors", [])
                for error in sentence_errors:
                    error_lower = error.lower()
                    if any(grammar_word in error_lower for grammar_word in ["grammar", "grammatical", "syntax", "syntactic"]):
                        error_categories.append("grammar")
                        error_details.append(f"Grammar: {error}")
                    elif any(punct_word in error_lower for punct_word in ["punctuation", "comma", "period", "question mark"]):
                        error_categories.append("punctuation")
                        error_details.append(f"Punctuation: {error}")
                    elif any(vocab_word in error_lower for vocab_word in ["vocabulary", "word choice", "lexical"]):
                        error_categories.append("vocabulary")
                        error_details.append(f"Vocabulary: {error}")
                    elif any(style_word in error_lower for style_word in ["style", "stylistic", "register"]):
                        error_categories.append("style")
                        error_details.append(f"Style: {error}")
                    else:
                        error_categories.append("general")
                        error_details.append(f"General: {error}")
            
            # Анализ ошибок ключевого слова
            if not word_analysis.get("overall_correct", True):
                word_errors = word_analysis.get("errors", [])
                for error in word_errors:
                    error_lower = error.lower()
                    if any(spell_word in error_lower for spell_word in ["spelling", "spelled", "spell"]):
                        error_categories.append("spelling")
                        error_details.append(f"Spelling: {error}")
                    elif any(grammar_word in error_lower for grammar_word in ["grammar", "grammatical", "form", "tense", "case"]):
                        error_categories.append("word_grammar")
                        error_details.append(f"Word Grammar: {error}")
                    elif any(context_word in error_lower for context_word in ["context", "contextual", "meaning", "semantic"]):
                        error_categories.append("context")
                        error_details.append(f"Context: {error}")
                    else:
                        error_categories.append("word_usage")
                        error_details.append(f"Word Usage: {error}")
            
            # Определение общего результата
            is_correct = (not sentence_analysis.get("has_errors", False) and 
                         word_analysis.get("overall_correct", True))
            
            # Определение типа ошибки для прогресса
            if word_analysis.get("spelling_correct", True) and word_analysis.get("grammar_correct", True) and not word_analysis.get("overall_correct", True):
                is_morphological_error = True
            else:
                is_morphological_error = False
            
            # Формируем объяснение на основе результатов анализа
            if is_correct:
                explanation = "Правильный ответ!"
            elif is_morphological_error:
                explanation = "Хороший смысл, но проверьте форму слова. Ответ принят!"
            else:
                if error_details:
                    explanation = f"Найдены ошибки: {'; '.join(error_details[:2])}"  # Показываем первые 2 ошибки
                else:
                    explanation = "Неправильный ответ"
            
            return {
                "is_correct": is_correct,
                "is_morphological_error": is_morphological_error,
                "is_synonym": False,  # Для заданий Translation синонимы не анализируются
                "explanation": explanation,
                "error_categories": list(set(error_categories)),  # Убираем дубликаты
                "error_details": error_details,
                "sentence_quality": sentence_analysis.get("overall_quality", "fair"),
                "word_analysis": word_analysis,
                "sentence_analysis": sentence_analysis
            }
            
        except Exception as e:
            print(f"Error classifying translation errors: {e}")
            return {
                "is_correct": False,
                "is_morphological_error": False,
                "is_synonym": False,
                "explanation": "Ошибка анализа ответа",
                "error_categories": ["analysis_error"],
                "error_details": ["Error analysis failed"],
                "sentence_quality": "unknown",
                "word_analysis": {},
                "sentence_analysis": {}
            }
    
    def analyze_fill_blank_answer(self, user_answer: str, correct_word: str, 
                                target_language: str, native_language: str) -> Dict:
        """Enhanced analysis for fill_blank tasks with synonym detection"""
        try:
            prompt = f"""Analyze if the user's answer is acceptable for a fill-in-the-blank exercise in {target_language}.

Correct answer: "{correct_word}"
User answer: "{user_answer}"

Consider the following criteria:
1. Exact match (10 points)
2. Synonym or alternative that fits the context (8-9 points)
3. Morphological variation (7-8 points)
4. Similar meaning but different form (6-7 points)
5. Wrong word (1-3 points)

Examples of acceptable alternatives:
- "Thank you" vs "Thanks" (both acceptable)
- "Hello" vs "Hi" (both acceptable)
- "Good" vs "Great" (both acceptable)
- "Help" vs "Assist" (both acceptable)

Rate the acceptability on a scale of 1-10 and provide analysis.

Respond in this format:
SCORE: [number]
ANALYSIS: [brief explanation]
TYPE: [exact/synonym/morphological/wrong]"""

            response = self.llm.invoke(prompt)
            result = response.content.strip()
            
            # Parse the response
            lines = result.split('\n')
            score = 0
            analysis_text = "Анализ ответа"
            answer_type = "unknown"
            
            for line in lines:
                if line.startswith("SCORE:"):
                    try:
                        score = int(line.split(":")[1].strip())
                    except:
                        score = 0
                elif line.startswith("ANALYSIS:"):
                    analysis_text = line.split(":", 1)[1].strip()
                elif line.startswith("TYPE:"):
                    answer_type = line.split(":", 1)[1].strip().lower()
            
            # Determine result based on score and type
            if score >= 9:
                return {
                    "is_correct": True,
                    "is_morphological_error": False,
                    "is_synonym": False,
                    "explanation": "Правильный ответ!"
                }
            elif score >= 7 and answer_type in ["synonym", "morphological"]:
                return {
                    "is_correct": False,
                    "is_morphological_error": answer_type == "morphological",
                    "is_synonym": answer_type == "synonym",
                    "explanation": "Хороший ответ! Это синоним или альтернативный вариант."
                }
            elif score >= 6:
                return {
                    "is_correct": False,
                    "is_morphological_error": True,
                    "is_synonym": False,
                    "explanation": "Хороший смысл, но проверьте форму слова. Ответ принят!"
                }
            else:
                return {
                    "is_correct": False,
                    "is_morphological_error": False,
                    "is_synonym": False,
                    "explanation": "Неправильный ответ"
                }
                
        except Exception as e:
            print(f"Error in fill_blank analysis: {e}")
            # Fallback to simple comparison
            is_correct = user_answer.lower().strip() == correct_word.lower().strip()
            return {
                "is_correct": is_correct,
                "is_morphological_error": False,
                "is_synonym": False,
                "explanation": "Проверка ответа выполнена" if is_correct else "Ответ неверный"
            }

