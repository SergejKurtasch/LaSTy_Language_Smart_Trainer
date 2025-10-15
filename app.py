"""
Main Streamlit application for Lasty Language Smart Trainer
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import io
from typing import List, Dict

# Import our modules
from database import DatabaseManager
from ai_service import AIService
from language_validator import LanguageValidator
from training_engine import TrainingEngine
from config import (
    SUPPORTED_LANGUAGES, PREFERRED_TOPICS, TRAINING_SESSION_LIMITS,
    IMPORT_ERROR_THRESHOLD, MAX_WORDS_PER_IMPORT
)

# Page configuration
st.set_page_config(
    page_title="Lasty: Language Smart Trainer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for mobile responsiveness and debugging
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        .stSelectbox, .stTextInput, .stTextArea {
            width: 100% !important;
        }
    }
    
    .training-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        background-color: #f9f9f9;
    }
    
    .correct-answer {
        color: #28a745;
        font-weight: bold;
    }
    
    .incorrect-answer {
        color: #dc3545;
        font-weight: bold;
    }
    
    .debug-info {
        background-color: #f0f0f0;
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        font-family: monospace;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'current_training' not in st.session_state:
    st.session_state.current_training = None
if 'current_task_index' not in st.session_state:
    st.session_state.current_task_index = 0

# Initialize services
@st.cache_resource
def get_services():
    """Initialize and cache services"""
    try:
        db = DatabaseManager()
        ai = AIService()
        validator = LanguageValidator()
        training_engine = TrainingEngine(db, ai)
        return db, ai, validator, training_engine
    except Exception as e:
        st.error(f"Failed to initialize services: {e}")
        return None, None, None, None

db, ai, validator, training_engine = get_services()

def login_page():
    """Display login/registration page"""
    st.title("🧠 Lasty: Language Smart Trainer")
    st.markdown("### Welcome to your personalized language learning experience!")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            login = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if not login or not password:
                    st.error("Please enter both username and password")
                else:
                    user = db.authenticate_user(login, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_id = user["user_id"]
                        st.session_state.user_data = user
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
    
    with tab2:
        st.subheader("Register")
        with st.form("register_form"):
            new_login = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            native_lang = st.selectbox("Native Language", list(SUPPORTED_LANGUAGES.keys()))
            learning_langs = st.multiselect("Languages to Learn", list(SUPPORTED_LANGUAGES.keys()))
            topics = st.multiselect("Preferred Topics", PREFERRED_TOPICS)
            
            submit_reg = st.form_submit_button("Register")
            
            if submit_reg:
                if not new_login or not new_password:
                    st.error("Please fill in all required fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif not learning_langs:
                    st.error("Please select at least one language to learn")
                else:
                    try:
                        user_id = db.create_user(
                            login=new_login,
                            password=new_password,
                            native_language=native_lang,
                            learning_languages=learning_langs,
                            preferred_topics=topics
                        )
                        st.success("Registration successful! Please login.")
                    except Exception as e:
                        st.error(f"Registration failed: {e}")

def dashboard():
    """Display main dashboard"""
    st.title("Lasty")
    st.markdown("### Language Smart Trainer")
    
    # User info sidebar
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.user_data['login']}!")
        st.write(f"Native: {st.session_state.user_data['native_language']}")
        st.write(f"Learning: {', '.join(st.session_state.user_data['learning_languages'])}")
        
        
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.user_data = None
            st.session_state.current_training = None
            st.rerun()
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 Dashboard", "📚 Words", "🎯 Training", "📊 Statistics"])
    
    with tab1:
        dashboard_content()
    
    with tab2:
        words_management()
    
    with tab3:
        training_session()
    
    with tab4:
        statistics_page()

def dashboard_content():
    """Display dashboard content"""
    st.subheader("Your Learning Progress")
    
    # Get user statistics
    user_id = st.session_state.user_id
    learning_languages = st.session_state.user_data['learning_languages']

    # Display statistics for each learning language in two columns
    stats_cols = st.columns(2)
    for idx, lang in enumerate(learning_languages):
        with stats_cols[idx % 2]:
            with st.expander(f"📈 Progress in {lang}", expanded=True):
                stats = db.get_user_statistics(user_id, lang)
                
                col1, col2, col3, col4 = st.columns(4)
                
                # Use custom CSS and HTML to reduce st.metric value font size and allow text to fit column
                def small_metric(label, value):
                    st.markdown(f"""
                        <div style="text-align: center;">
                            <span style="font-size: 0.8rem; color: #888;">{label}</span><br>
                            <span style="font-size: 1.5rem; font-weight: bold; word-break: break-word;">{value}</span>
                        </div>
                    """, unsafe_allow_html=True)

                with col1:
                    small_metric("Total Words", stats['total_words'])
                
                with col2:
                    small_metric("Ready for Training", stats.get('words_ready_for_training', 0))
                
                with col3:
                    small_metric("Recent Activity", f"{stats.get('recent_activity', 0)} words")
                
                with col4:
                    total_words = stats.get('total_words', 0)
                    if total_words > 0:
                        completed = stats.get('progress_distribution', {}).get('100', 0)
                        completion_rate = (completed / total_words) * 100
                        small_metric("Completion Rate", f"{completion_rate:.1f}%")
                    else:
                        small_metric("Completion Rate", "0%")
                
                # Progress distribution chart
                progress_dist = stats.get('progress_distribution', {})
                if progress_dist:
                    st.subheader("Progress Distribution")
                    progress_df = pd.DataFrame(
                        list(progress_dist.items()),
                        columns=['Progress Level', 'Count']
                    )
                    st.bar_chart(progress_df.set_index('Progress Level'))

def words_management():
    """Display words management interface"""
    st.subheader("📚 Word Management")
    
    # Import words section
    with st.expander("📥 Import Words", expanded=True):
        st.write("Upload a CSV or TXT file with word pairs (native language, target language)")
        
        # Language selection
        col1, col2 = st.columns(2)
        with col1:
            target_language = st.selectbox("Target Language", st.session_state.user_data['learning_languages'])
        
        with col2:
            st.write("File format: CSV or TXT, 2 columns, no header")
        
        # File upload
        uploaded_file = st.file_uploader("Choose file", type=['csv', 'txt'])
        
        if uploaded_file:
            try:
                # Read file content
                if uploaded_file.type == "text/csv":
                    df = pd.read_csv(uploaded_file, header=None)
                else:
                    content = uploaded_file.read().decode('utf-8')
                    lines = content.strip().split('\n')
                    # Use more robust parsing for comma-separated values
                    import csv
                    import io
                    csv_content = io.StringIO(content)
                    reader = csv.reader(csv_content)
                    rows = list(reader)
                    df = pd.DataFrame(rows)
                
                if df.shape[1] < 2:
                    st.error("File must have at least 2 columns")
                else:
                    # Limit number of words
                    if len(df) > MAX_WORDS_PER_IMPORT:
                        st.warning(f"File has {len(df)} words. Only first {MAX_WORDS_PER_IMPORT} will be imported.")
                        df = df.head(MAX_WORDS_PER_IMPORT)
                    
                    # Create word pairs - first column is English, second is target language
                    # For your file: English words -> Russian translations
                    word_pairs = [(row[0], row[1]) for _, row in df.iterrows()]
                    
                    # Debug: show first few word pairs
                    st.write("**First 3 word pairs:**")
                    for i, (native, target) in enumerate(word_pairs[:3]):
                        st.write(f"{i+1}. {native} → {target}")
                    
                    # Validate words (English -> target language)
                    validation_result = validator.validate_word_pairs(
                        word_pairs, 
                        "English",  # Source language is always English for this file
                        target_language
                    )
                    
                    # Show validation results
                    st.write(f"**Validation Results:**")
                    st.write(f"- Valid pairs: {len(validation_result['valid_pairs'])}")
                    st.write(f"- Invalid pairs: {len(validation_result['invalid_pairs'])}")
                    st.write(f"- Error rate: {validation_result['error_rate']:.1%}")
                    
                    if validation_result['error_rate'] > IMPORT_ERROR_THRESHOLD:
                        st.warning(f"Error rate ({validation_result['error_rate']:.1%}) exceeds threshold ({IMPORT_ERROR_THRESHOLD:.1%})")
                        
                        if st.button("Continue Import"):
                            import_result = db.import_word_pairs(
                                st.session_state.user_id, 
                                validation_result['valid_pairs'], 
                                target_language
                            )
                            st.success(f"Imported {import_result['imported']} words successfully!")
                    else:
                        if st.button("Import Words"):
                            try:
                                import_result = db.import_word_pairs(
                                    st.session_state.user_id, 
                                    validation_result['valid_pairs'], 
                                    target_language
                                )
                                st.success(f"Imported {import_result['imported']} words successfully!")
                                if import_result['duplicates'] > 0:
                                    st.info(f"Skipped {import_result['duplicates']} duplicate words")
                                if import_result['errors']:
                                    st.warning(f"Errors: {len(import_result['errors'])} words failed to import")
                                    for error in import_result['errors'][:5]:  # Show first 5 errors
                                        st.write(f"- {error[0]} → {error[1]}: {error[2]}")
                            except Exception as e:
                                st.error(f"Import failed: {e}")
            
            except Exception as e:
                st.error(f"Error processing file: {e}")
    
    # Display existing words
    with st.expander("📋 Your Words", expanded=True):
        target_language = st.selectbox("Select Language", st.session_state.user_data['learning_languages'], key="words_lang")
        
        if target_language:
            words = db.get_user_words(st.session_state.user_id, target_language)
            
            if words:
                # Create words dataframe
                words_df = pd.DataFrame(words)
                words_df = words_df[['native_word', 'target_word', 'progress', 'last_training_date', 'next_training_date']]
                words_df.columns = ['Native Word', 'Target Word', 'Progress (%)', 'Last Training', 'Next Training']
                
                # Display with search
                search_term = st.text_input("Search words", key="search_words")
                if search_term:
                    mask = words_df['Native Word'].str.contains(search_term, case=False) | \
                           words_df['Target Word'].str.contains(search_term, case=False)
                    words_df = words_df[mask]
                
                st.dataframe(words_df, use_container_width=True)
                
                # Delete word option
                if st.button("Delete Selected Words"):
                    st.info("Word deletion feature will be implemented in the next version")
            else:
                st.info("No words found. Import some words to get started!")

def training_session():
    """Display training session interface"""
    st.subheader("🎯 Training Session")
    
    if st.session_state.current_training is None:
        # Start new training session
        col1, col2 = st.columns(2)
        
        with col1:
            target_language = st.selectbox("Select Language", st.session_state.user_data['learning_languages'])
        
        with col2:
            session_limit = st.selectbox("Words per Session", TRAINING_SESSION_LIMITS)
        
        if st.button("Start Training Session", type="primary"):
            result = training_engine.start_training_session(
                st.session_state.user_id, 
                target_language, 
                session_limit
            )
            
            if result['success']:
                st.session_state.current_training = result
                st.session_state.current_task_index = 0
                st.success(f"Training session started! {result['total_tasks']} words to practice.")
                st.rerun()
            else:
                st.error(result['error'])
    
    else:
        # Display current training task
        current_task = st.session_state.current_training['tasks'][st.session_state.current_task_index]
        total_tasks = st.session_state.current_training['total_tasks']
        
        st.write(f"**Task {st.session_state.current_task_index + 1} of {total_tasks}**")
        
        # Progress bar
        progress = (st.session_state.current_task_index + 1) / total_tasks
        st.progress(progress)
        
        # Display task
        with st.container():
            st.markdown(f"### {current_task['instruction']}")
            
            if current_task['task_type'] == 'translation':
                user_answer = st.text_input("Your answer:", key=f"answer_{current_task['task_id']}")
                
            elif current_task['task_type'] == 'multiple_choice':
                # Show sentence if available
                if 'sentence' in current_task:
                    st.write(f"**Sentence:** {current_task['sentence']}")
                    st.write(f"**Context:** {current_task['sentence_translation']}")
                
                user_answer = st.radio(
                    "Choose the correct answer:",
                    current_task['options'],
                    key=f"answer_{current_task['task_id']}"
                )
                
            elif current_task['task_type'] == 'fill_blank':
                st.write(f"**Sentence:** {current_task['sentence']}")
                st.write(f"**Context:** {current_task['sentence_translation']}")
                user_answer = st.text_input("Fill in the blank:", key=f"answer_{current_task['task_id']}")
            
            # Check if answer was already submitted
            if f"answer_submitted_{current_task['task_id']}" not in st.session_state:
                # Submit button
                if st.button("Submit Answer", type="primary"):
                    if user_answer and user_answer.strip():
                        result = training_engine.submit_answer(
                            current_task['task_id'], 
                            user_answer, 
                            st.session_state.user_id
                        )
                        
                        if result['success']:
                            # Store result in session state
                            st.session_state[f"answer_result_{current_task['task_id']}"] = result
                            st.session_state[f"answer_submitted_{current_task['task_id']}"] = True
                            st.rerun()
                    else:
                        st.warning("Please enter an answer")
            else:
                # Show result if already submitted
                result = st.session_state[f"answer_result_{current_task['task_id']}"]
                
                # Show result
                if result.get('message'):
                    if result['is_correct']:
                        st.success(result['message'])
                    elif result['is_morphological_error']:
                        st.warning(result['message'])
                    elif result['is_synonym']:
                        st.info(result['message'])
                    else:
                        st.error(result['message'])
                else:
                    # Fallback to old format
                    if result['is_correct']:
                        st.success("✅ " + result.get('message', 'Correct!'))
                    elif result['is_morphological_error']:
                        st.warning("⚠️ " + result.get('message', 'Almost correct!'))
                    elif result['is_synonym']:
                        st.info("ℹ️ " + result.get('message', 'Good synonym!'))
                    else:
                        st.error("❌ " + result.get('message', 'Incorrect!'))
                
                st.write(f"**Explanation:** {result['explanation']}")
                st.write(f"**New Progress:** {result['new_progress']}%")
                
                # Next button
                if st.session_state.current_task_index < total_tasks - 1:
                    if st.button("Следующее слово", type="primary"):
                        st.session_state.current_task_index += 1
                        st.rerun()
                else:
                    if st.button("Завершить тренировку", type="primary"):
                        st.success("🎉 Training session completed!")
                        st.session_state.current_training = None
                        st.session_state.current_task_index = 0
                        st.rerun()
        
        # Cancel session button
        if st.button("Cancel Session"):
            st.session_state.current_training = None
            st.session_state.current_task_index = 0
            st.rerun()

def statistics_page():
    """Display statistics page"""
    st.subheader("📊 Learning Statistics")
    
    user_id = st.session_state.user_id
    learning_languages = st.session_state.user_data['learning_languages']
    
    # Language selection
    selected_language = st.selectbox("Select Language", learning_languages, key="stats_language")
    
    if selected_language:
        # Get statistics
        stats = db.get_user_statistics(user_id, selected_language)
        errors = db.get_user_errors(user_id, selected_language)
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Words", stats['total_words'])
        
        with col2:
            st.metric("Ready for Training", stats.get('words_ready_for_training', 0))
        
        with col3:
            st.metric("Recent Activity (7 days)", stats.get('recent_activity', 0))
        
        # Progress distribution
        progress_dist = stats.get('progress_distribution', {})
        if progress_dist:
            st.subheader("Progress Distribution")
            progress_df = pd.DataFrame(
                list(progress_dist.items()),
                columns=['Progress Level', 'Count']
            )
            st.bar_chart(progress_df.set_index('Progress Level'))
        
        # Common errors
        if errors:
            st.subheader("Common Errors")
            errors_df = pd.DataFrame(errors)
            errors_df = errors_df[['description', 'count']].head(10)
            errors_df.columns = ['Error Type', 'Count']
            st.dataframe(errors_df, use_container_width=True)
        else:
            st.info("No errors recorded yet. Keep practicing!")

# Main application logic
def main():
    """Main application function"""
    if not db or not ai or not validator or not training_engine:
        st.error("Application services failed to initialize. Please check your configuration.")
        return
    
    if not st.session_state.authenticated:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()
