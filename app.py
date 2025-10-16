"""
Main Streamlit application for Lasty Language Smart Trainer
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import io
from typing import List, Dict
import logging

# Import our modules
from database import DatabaseManager
from ai_service import AIService
from training_engine import TrainingEngine
from config import (
    SUPPORTED_LANGUAGES, PREFERRED_TOPICS, TRAINING_SESSION_LIMITS,
    IMPORT_ERROR_THRESHOLD, MAX_WORDS_PER_IMPORT, INTERFACE_LANGUAGES
)
from translations import (
    get_translation, get_user_language_index, LANGUAGE_INDICES,
    app_title, welcome_message, tab_dashboard, tab_words, tab_training, tab_statistics, tab_settings,
    login_tab, register_tab, username_label, password_label, confirm_password_label,
    login_button, register_button, native_language_label, learning_languages_label,
    preferred_topics_label, error_required_fields, error_passwords_match,
    error_select_language, error_invalid_credentials, error_registration_failed,
    success_login, success_registration, sidebar_welcome, sidebar_native,
    sidebar_learning, logout_button, words_management_title, import_words_title,
    your_words_title, import_instructions, target_language_label, file_format_info,
    column_order_label, column_order_option1, column_order_option2, choose_file_label,
    import_button, continue_import_button, training_title, select_language_label,
    words_per_session_label, start_training_button, task_progress, of_label,
    progress_label, submit_answer_button, next_word_button, finish_training_button,
    cancel_session_button, statistics_title, total_words_label, ready_for_training_label,
    recent_activity_label, completion_rate_label, progress_distribution_label,
    common_errors_label, no_errors_message, correct_answer, almost_correct,
    good_synonym, incorrect_answer, explanation_label, new_progress_label,
    no_words_found, training_completed, validation_results, valid_pairs,
    invalid_pairs, error_rate, your_answer_label, sentence_label, context_label,
    choose_correct_answer, fill_blank_label, please_enter_answer, correct_translation,
    choose_english_translation, correct_good_job, auto_detection_enabled,
    analyzing_languages, languages_detected, left_column_native, right_column_target,
    cleaned_words_preview, detection_failed, check_file_content,
    settings_title, learning_languages_settings, preferred_topics_settings,
    interface_language_settings, save_settings_button, settings_saved_success,
    settings_save_error
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lasty_language_detection.log'),
        logging.StreamHandler()
    ]
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
        training_engine = TrainingEngine(db, ai)
        return db, ai, training_engine
    except Exception as e:
        st.error(f"Failed to initialize services: {e}")
        return None, None, None

db, ai, training_engine = get_services()

def get_user_interface_language():
    """Получить язык интерфейса для текущего пользователя"""
    if st.session_state.user_data and 'interface_language' in st.session_state.user_data:
        return get_user_language_index(st.session_state.user_data['interface_language'])
    return 0  # По умолчанию английский

def login_page():
    """Display login/registration page"""
    # Для страницы входа используем английский по умолчанию
    lang_idx = 0
    
    st.title(f"🧠 {get_translation(app_title, lang_idx)}")
    st.markdown(f"### {get_translation(welcome_message, lang_idx)}")
    
    tab1, tab2 = st.tabs([get_translation(login_tab, lang_idx), get_translation(register_tab, lang_idx)])
    
    with tab1:
        st.subheader(get_translation(login_tab, lang_idx))
        with st.form("login_form"):
            login = st.text_input(get_translation(username_label, lang_idx))
            password = st.text_input(get_translation(password_label, lang_idx), type="password")
            submit = st.form_submit_button(get_translation(login_button, lang_idx))
            
            if submit:
                if not login or not password:
                    st.error(get_translation(error_required_fields, lang_idx))
                else:
                    user = db.authenticate_user(login, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_id = user["user_id"]
                        st.session_state.user_data = user
                        st.success(get_translation(success_login, lang_idx))
                        st.rerun()
                    else:
                        st.error(get_translation(error_invalid_credentials, lang_idx))
    
    with tab2:
        st.subheader(get_translation(register_tab, lang_idx))
        with st.form("register_form"):
            new_login = st.text_input(get_translation(username_label, lang_idx))
            new_password = st.text_input(get_translation(password_label, lang_idx), type="password")
            confirm_password = st.text_input(get_translation(confirm_password_label, lang_idx), type="password")
            
            native_lang = st.selectbox(get_translation(native_language_label, lang_idx), list(SUPPORTED_LANGUAGES.keys()))
            learning_langs = st.multiselect(get_translation(learning_languages_label, lang_idx), list(SUPPORTED_LANGUAGES.keys()))
            topics = st.multiselect(get_translation(preferred_topics_label, lang_idx), PREFERRED_TOPICS)
            
            # Добавляем выбор языка интерфейса
            interface_lang = st.selectbox("Interface Language", list(INTERFACE_LANGUAGES.keys()), 
                                        help="Choose the language for the user interface")
            
            submit_reg = st.form_submit_button(get_translation(register_button, lang_idx))
            
            if submit_reg:
                if not new_login or not new_password:
                    st.error(get_translation(error_required_fields, lang_idx))
                elif new_password != confirm_password:
                    st.error(get_translation(error_passwords_match, lang_idx))
                elif not learning_langs:
                    st.error(get_translation(error_select_language, lang_idx))
                else:
                    try:
                        user_id = db.create_user(
                            login=new_login,
                            password=new_password,
                            native_language=native_lang,
                            learning_languages=learning_langs,
                            preferred_topics=topics,
                            interface_language=interface_lang
                        )
                        st.success(get_translation(success_registration, lang_idx))
                    except Exception as e:
                        st.error(f"{get_translation(error_registration_failed, lang_idx)}: {e}")

def dashboard():
    """Display main dashboard"""
    # Получаем язык интерфейса пользователя
    lang_idx = get_user_interface_language()
    
    st.title("Lasty")
    st.markdown(f"### {get_translation(app_title, lang_idx)}")
    
    # User info sidebar
    with st.sidebar:
        st.write(f"{get_translation(sidebar_welcome, lang_idx)}, {st.session_state.user_data['login']}!")
        st.write(f"{get_translation(sidebar_native, lang_idx)}: {st.session_state.user_data['native_language']}")
        st.write(f"{get_translation(sidebar_learning, lang_idx)}: {', '.join(st.session_state.user_data['learning_languages'])}")
        
        
        if st.button(get_translation(logout_button, lang_idx)):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.user_data = None
            st.session_state.current_training = None
            st.rerun()
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        get_translation(tab_dashboard, lang_idx), 
        get_translation(tab_words, lang_idx), 
        get_translation(tab_training, lang_idx), 
        get_translation(tab_statistics, lang_idx),
        get_translation(tab_settings, lang_idx)
    ])
    
    with tab1:
        dashboard_content()
    
    with tab2:
        words_management()
    
    with tab3:
        training_session()
    
    with tab4:
        statistics_page()
    
    with tab5:
        settings_page()

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
    lang_idx = get_user_interface_language()
    st.subheader(get_translation(words_management_title, lang_idx))
    
    # Import words section
    with st.expander(get_translation(import_words_title, lang_idx), expanded=True):
        st.write(get_translation(import_instructions, lang_idx))
        
        # Language selection
        col1, col2 = st.columns(2)
        with col1:
            target_language = st.selectbox(get_translation(target_language_label, lang_idx), st.session_state.user_data['learning_languages'])
        
        with col2:
            st.write(get_translation(file_format_info, lang_idx))
            
        # Automatic language detection is always enabled
        st.info(get_translation(auto_detection_enabled, lang_idx))
        
        # File upload
        uploaded_file = st.file_uploader(get_translation(choose_file_label, lang_idx), type=['csv', 'txt'])
        
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
                    
                    # Get user's native language for validation
                    user_native_language = st.session_state.user_data.get('native_language', 'English')
                    
                    # Automatic language detection (always enabled)
                    st.info(get_translation(analyzing_languages, lang_idx))
                    
                    # Extract columns
                    left_column = [str(row[0]) for _, row in df.iterrows()]
                    right_column = [str(row[1]) for _, row in df.iterrows()]
                    
                    # Use AI to detect languages
                    logging.info(f"Starting language detection for user {st.session_state.user_id}")
                    logging.info(f"Target language: {target_language}, Native language: {user_native_language}")
                    logging.info(f"Left column sample: {left_column[:5]}")
                    logging.info(f"Right column sample: {right_column[:5]}")
                    
                    detection_result = ai.auto_detect_column_languages(
                        left_column, right_column, target_language, user_native_language
                    )
                    
                    logging.info(f"Detection result: {detection_result}")
                    
                    if detection_result['success']:
                        # Create word pairs from detected languages
                        word_pairs = list(zip(detection_result['native_words'], detection_result['target_words']))
                        
                        st.success(get_translation(languages_detected, lang_idx))
                        st.write(get_translation(left_column_native, lang_idx).format(column=detection_result['native_column']))
                        st.write(get_translation(right_column_target, lang_idx).format(column=detection_result['target_column']))
                        
                        # Show cleaned words
                        st.write(get_translation(cleaned_words_preview, lang_idx))
                        for i, (native, target) in enumerate(word_pairs[:3]):
                            st.write(f"{i+1}. {native} → {target}")
                        
                        # Skip validation for auto-detected words (they're already cleaned)
                        validation_result = {
                            'valid_pairs': word_pairs,
                            'invalid_pairs': [],
                            'error_rate': 0.0
                        }
                        
                    else:
                        st.error(get_translation(detection_failed, lang_idx).format(error=detection_result['error']))
                        st.write(get_translation(check_file_content, lang_idx))
                        return
                    
                    # Show validation results
                    st.write(f"**{get_translation(validation_results, lang_idx)}:**")
                    st.write(f"- {get_translation(valid_pairs, lang_idx)}: {len(validation_result['valid_pairs'])}")
                    st.write(f"- {get_translation(invalid_pairs, lang_idx)}: {len(validation_result['invalid_pairs'])}")
                    st.write(f"- {get_translation(error_rate, lang_idx)}: {validation_result['error_rate']:.1%}")
                    
                    if validation_result['error_rate'] > IMPORT_ERROR_THRESHOLD:
                        st.warning(f"Error rate ({validation_result['error_rate']:.1%}) exceeds threshold ({IMPORT_ERROR_THRESHOLD:.1%})")
                        
                        if st.button(get_translation(continue_import_button, lang_idx)):
                            import_result = db.import_word_pairs(
                                st.session_state.user_id, 
                                validation_result['valid_pairs'], 
                                target_language
                            )
                            st.success(f"Imported {import_result['imported']} words successfully!")
                    else:
                        if st.button(get_translation(import_button, lang_idx)):
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
    with st.expander(get_translation(your_words_title, lang_idx), expanded=True):
        target_language = st.selectbox(get_translation(select_language_label, lang_idx), st.session_state.user_data['learning_languages'], key="words_lang")
        
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
                
                st.dataframe(words_df, width='stretch')
                
                # Delete word option
                if st.button("Delete Selected Words"):
                    st.info("Word deletion feature will be implemented in the next version")
            else:
                st.info(get_translation(no_words_found, lang_idx))

def training_session():
    """Display training session interface"""
    lang_idx = get_user_interface_language()
    st.subheader(get_translation(training_title, lang_idx))
    
    if st.session_state.current_training is None:
        # Start new training session
        col1, col2 = st.columns(2)
        
        with col1:
            target_language = st.selectbox(get_translation(select_language_label, lang_idx), st.session_state.user_data['learning_languages'])
        
        with col2:
            session_limit = st.selectbox(get_translation(words_per_session_label, lang_idx), TRAINING_SESSION_LIMITS)
        
        if st.button(get_translation(start_training_button, lang_idx), type="primary"):
            result = training_engine.start_training_session(
                st.session_state.user_id, 
                target_language, 
                session_limit
            )
            
            if result['success']:
                # Store session info for lazy loading
                st.session_state.current_training = {
                    'session_id': result['session_id'],
                    'current_task': result['current_task'],
                    'current_task_index': result['current_task_index'],
                    'total_tasks': result['total_tasks']
                }
                st.success(f"Training session started! {result['total_tasks']} words to practice.")
                st.rerun()
            else:
                st.error(result['error'])
    
    else:
        # Display current training task
        current_task = st.session_state.current_training['current_task']
        total_tasks = st.session_state.current_training['total_tasks']
        current_task_index = st.session_state.current_training['current_task_index']
        
        # Prepare next task in background while user is thinking
        training_engine.prepare_next_task_in_background(st.session_state.current_training['session_id'])
        
        st.write(f"**{get_translation(task_progress, lang_idx)} {current_task_index + 1} {get_translation(of_label, lang_idx)} {total_tasks}**")
        
        # Progress bar
        progress = (current_task_index + 1) / total_tasks
        st.progress(progress)
        
        # Display task
        with st.container():
            # Debug information
            if 'debug_info' in current_task:
                debug_info = current_task['debug_info']
                st.info(f"🔍 **DEBUG INFO:** Тип задания: `{debug_info['task_type']}` | Метод: `{debug_info['method']}` | Прогресс: `{debug_info['progress']}%`")
            
            st.markdown(f"### {current_task['instruction']}")
            
            if current_task['task_type'] == 'translation':
                # Show sentence and context if available (same as other task types)
                if 'sentence' in current_task and current_task['sentence']:
                    st.write(f"**{get_translation(sentence_label, lang_idx)}** {current_task['sentence']}")
                if 'sentence_translation' in current_task and current_task['sentence_translation']:
                    st.write(f"**{get_translation(context_label, lang_idx)}** {current_task['sentence_translation']}")
                
                user_answer = st.text_input(get_translation(your_answer_label, lang_idx), key=f"answer_{current_task['task_id']}")
                
            elif current_task['task_type'] == 'multiple_choice':
                # Show sentence if available
                if 'sentence' in current_task:
                    st.write(f"**{get_translation(sentence_label, lang_idx)}** {current_task['sentence']}")
                    st.write(f"**{get_translation(context_label, lang_idx)}** {current_task['sentence_translation']}")
                
                user_answer = st.radio(
                    get_translation(choose_correct_answer, lang_idx),
                    current_task['options'],
                    key=f"answer_{current_task['task_id']}"
                )
                
            elif current_task['task_type'] == 'fill_blank':
                st.write(f"**{get_translation(sentence_label, lang_idx)}** {current_task['sentence']}")
                st.write(f"**{get_translation(context_label, lang_idx)}** {current_task['sentence_translation']}")
                user_answer = st.text_input(get_translation(fill_blank_label, lang_idx), key=f"answer_{current_task['task_id']}")
            
            # Check if answer was already submitted
            if f"answer_submitted_{current_task['task_id']}" not in st.session_state:
                # Submit button
                if st.button(get_translation(submit_answer_button, lang_idx), type="primary"):
                    if user_answer and user_answer.strip():
                        result = training_engine.submit_answer(
                            current_task['task_id'], 
                            user_answer, 
                            st.session_state.user_id,
                            st.session_state.current_training['session_id']
                        )
                        
                        if result['success']:
                            # Store result in session state
                            st.session_state[f"answer_result_{current_task['task_id']}"] = result
                            st.session_state[f"answer_submitted_{current_task['task_id']}"] = True
                            st.rerun()
                    else:
                        st.warning(get_translation(please_enter_answer, lang_idx))
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
                
                st.write(f"**{get_translation(explanation_label, lang_idx)}:** {result['explanation']}")
                st.write(f"**{get_translation(new_progress_label, lang_idx)}:** {result['new_progress']}%")
                
                
                # Next button
                if current_task_index < total_tasks - 1:
                    if st.button(get_translation(next_word_button, lang_idx), type="primary"):
                        # Get next task using lazy loading
                        next_result = training_engine.get_next_task(st.session_state.current_training['session_id'])
                        if next_result['success']:
                            st.session_state.current_training['current_task'] = next_result['current_task']
                            st.session_state.current_training['current_task_index'] = next_result['current_task_index']
                            st.rerun()
                        else:
                            st.error(f"Failed to get next task: {next_result['error']}")
                else:
                    if st.button(get_translation(finish_training_button, lang_idx), type="primary"):
                        st.success(get_translation(training_completed, lang_idx))
                        st.session_state.current_training = None
                        st.session_state.current_task_index = 0
                        st.rerun()
        
        # Cancel session button
        if st.button(get_translation(cancel_session_button, lang_idx)):
            st.session_state.current_training = None
            st.session_state.current_task_index = 0
            st.rerun()

def statistics_page():
    """Display statistics page"""
    lang_idx = get_user_interface_language()
    st.subheader(get_translation(statistics_title, lang_idx))
    
    user_id = st.session_state.user_id
    learning_languages = st.session_state.user_data['learning_languages']
    
    # Language selection
    selected_language = st.selectbox(get_translation(select_language_label, lang_idx), learning_languages, key="stats_language")
    
    if selected_language:
        # Get statistics
        stats = db.get_user_statistics(user_id, selected_language)
        errors = db.get_user_errors(user_id, selected_language)
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(get_translation(total_words_label, lang_idx), stats['total_words'])
        
        with col2:
            st.metric(get_translation(ready_for_training_label, lang_idx), stats.get('words_ready_for_training', 0))
        
        with col3:
            st.metric(get_translation(recent_activity_label, lang_idx), stats.get('recent_activity', 0))
        
        # Progress distribution
        progress_dist = stats.get('progress_distribution', {})
        if progress_dist:
            st.subheader(get_translation(progress_distribution_label, lang_idx))
            progress_df = pd.DataFrame(
                list(progress_dist.items()),
                columns=['Progress Level', 'Count']
            )
            st.bar_chart(progress_df.set_index('Progress Level'))
        
        # Common errors
        if errors:
            st.subheader(get_translation(common_errors_label, lang_idx))
            errors_df = pd.DataFrame(errors)
            errors_df = errors_df[['description', 'count']].head(10)
            errors_df.columns = ['Error Type', 'Count']
            st.dataframe(errors_df, width='stretch')
        else:
            st.info(get_translation(no_errors_message, lang_idx))

def settings_page():
    """Display user settings page"""
    lang_idx = get_user_interface_language()
    st.subheader(get_translation(settings_title, lang_idx))
    
    # Get current user data
    user_data = st.session_state.user_data
    
    with st.form("settings_form"):
        st.markdown("### " + get_translation(learning_languages_settings, lang_idx))
        current_learning_languages = user_data.get('learning_languages', [])
        new_learning_languages = st.multiselect(
            get_translation(learning_languages_settings, lang_idx),
            list(SUPPORTED_LANGUAGES.keys()),
            default=current_learning_languages,
            key="settings_learning_languages"
        )
        
        st.markdown("### " + get_translation(preferred_topics_settings, lang_idx))
        current_topics = user_data.get('preferred_topics', [])
        new_topics = st.multiselect(
            get_translation(preferred_topics_settings, lang_idx),
            PREFERRED_TOPICS,
            default=current_topics,
            key="settings_topics"
        )
        
        st.markdown("### " + get_translation(interface_language_settings, lang_idx))
        current_interface_language = user_data.get('interface_language', 'English')
        new_interface_language = st.selectbox(
            get_translation(interface_language_settings, lang_idx),
            list(INTERFACE_LANGUAGES.keys()),
            index=list(INTERFACE_LANGUAGES.keys()).index(current_interface_language) if current_interface_language in INTERFACE_LANGUAGES else 0,
            key="settings_interface_language"
        )
        
        # Save button
        save_button = st.form_submit_button(get_translation(save_settings_button, lang_idx), type="primary")
        
        if save_button:
            # Validate that at least one learning language is selected
            if not new_learning_languages:
                st.error(get_translation(error_select_language, lang_idx))
            else:
                try:
                    # Update learning languages
                    if new_learning_languages != current_learning_languages:
                        success = db.update_user_languages(st.session_state.user_id, new_learning_languages)
                        if success:
                            st.session_state.user_data['learning_languages'] = new_learning_languages
                        else:
                            st.error(get_translation(settings_save_error, lang_idx))
                            return
                    
                    # Update preferred topics
                    if new_topics != current_topics:
                        success = db.update_user_topics(st.session_state.user_id, new_topics)
                        if success:
                            st.session_state.user_data['preferred_topics'] = new_topics
                        else:
                            st.error(get_translation(settings_save_error, lang_idx))
                            return
                    
                    # Update interface language
                    if new_interface_language != current_interface_language:
                        success = db.update_user_interface_language(st.session_state.user_id, new_interface_language)
                        if success:
                            st.session_state.user_data['interface_language'] = new_interface_language
                            # Reload the page to apply new interface language
                            st.success(get_translation(settings_saved_success, lang_idx))
                            st.rerun()
                        else:
                            st.error(get_translation(settings_save_error, lang_idx))
                            return
                    
                    # If we get here, all updates were successful
                    st.success(get_translation(settings_saved_success, lang_idx))
                    
                except Exception as e:
                    st.error(f"{get_translation(settings_save_error, lang_idx)}: {e}")

# Main application logic
def main():
    """Main application function"""
    if not db or not ai or not training_engine:
        st.error("🚨 **Ошибка инициализации приложения**")
        st.markdown("""
        ### Не удалось инициализировать сервисы приложения
        
        **Возможные причины:**
        1. **Отсутствуют переменные окружения** - проверьте файл `.env`
        2. **Неправильные API ключи** - проверьте подключение к Supabase и OpenAI
        
        **Что нужно сделать:**
        1. Откройте файл `.env` в корневой папке проекта
        2. Замените заглушки на реальные значения:
           - `SUPABASE_URL` - URL вашей базы данных Supabase
           - `SUPABASE_KEY` - API ключ Supabase
           - `OPENAI_API_KEY` - API ключ OpenAI
        
        **Пример файла .env:**
        ```
        SUPABASE_URL=https://your-project.supabase.co
        SUPABASE_KEY=your_supabase_anon_key
        OPENAI_API_KEY=sk-your_openai_api_key
        ```
        
        После настройки перезапустите приложение.
        """)
        
        st.markdown("---")
        st.markdown("**Текущие переменные окружения:**")
        try:
            from config import SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**SUPABASE_URL:** {'✅ Настроен' if SUPABASE_URL and SUPABASE_URL != 'your_supabase_url_here' else '❌ Не настроен'}")
            with col2:
                st.write(f"**SUPABASE_KEY:** {'✅ Настроен' if SUPABASE_KEY and SUPABASE_KEY != 'your_supabase_key_here' else '❌ Не настроен'}")
            with col3:
                st.write(f"**OPENAI_API_KEY:** {'✅ Настроен' if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_api_key_here' else '❌ Не настроен'}")
        except Exception as e:
            st.error(f"Ошибка загрузки конфигурации: {e}")
        
        return
    
    if not st.session_state.authenticated:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()
