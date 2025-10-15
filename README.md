# Lasty: Language Smart Trainer

A web application for language learning practice using AI for sentence generation, user progress tracking, and error analysis.

## Features

- **User Authentication**: Simple login/registration system
- **Word Import**: CSV/TXT file import with language validation
- **Smart Training**: AI-powered sentence generation and error analysis
- **Progress Tracking**: Ebbinghaus forgetting curve algorithm
- **Multiple Task Types**: Translation, multiple choice, fill-in-the-blank
- **Error Analysis**: AI-powered error classification and tracking
- **Mobile Responsive**: Optimized for mobile devices

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **Database**: Supabase
- **AI**: OpenAI GPT-4o/GPT-4o-mini
- **Language Validation**: FastText API
- **Deployment**: Streamlit Cloud

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd LaSTy_Language_Smart_Trainer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the application:
```bash
streamlit run app.py
```

## Configuration

Create a `.env` file with the following variables:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# FastText API Configuration (optional)
FASTTEXT_API_URL=your_fasttext_api_url_here
FASTTEXT_API_KEY=your_fasttext_api_key_here
```

## Database Schema

### Users Table
- `user_id` (UUID, Primary Key)
- `login` (Text)
- `password_hash` (Text)
- `native_language` (Text)
- `learning_languages` (Array)
- `preferred_topics` (Array)
- `interface_language` (Text)
- `is_admin` (Boolean)

### Word Pairs Table
- `word_id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key)
- `native_word` (Text)
- `target_word` (Text)
- `progress` (Integer, 0-100)
- `last_training_date` (Date)
- `next_training_date` (Date)
- `language` (Text)

### Errors Table
- `error_id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key)
- `language` (Text)
- `description` (Text)
- `count` (Integer)

## Usage

1. **Registration**: Create an account with your native language and learning preferences
2. **Import Words**: Upload CSV/TXT files with word pairs
3. **Training**: Start training sessions with AI-generated content
4. **Progress**: Track your learning progress and common errors
5. **Statistics**: View detailed learning analytics

## Training Algorithm

The application uses the Ebbinghaus forgetting curve with the following intervals:

- **0-19%**: 1 day (Initial Memorization)
- **20-39%**: 3 days (First Repetition)
- **40-59%**: 7 days (Medium Stage)
- **60-79%**: 14 days (Consolidation)
- **80-99%**: 30 days (Control Repetition)
- **100%**: 120 days (Long-term Retention)

## Task Types

- **Translation**: Direct translation input
- **Multiple Choice**: Choose from 3 options
- **Fill-in-the-Blank**: Complete sentences with target words

Task type probability depends on word progress:
- **Low Progress (0-40%)**: Higher probability of multiple choice
- **Medium Progress (41-70%)**: Higher probability of fill-in-the-blank
- **High Progress (71-100%)**: Higher probability of translation

## API Endpoints

- `/register` - User registration
- `/login` - User authentication
- `/logout` - User logout
- `/upload_words` - Import word pairs
- `/delete_word` - Remove word pairs
- `/get_words` - Retrieve user words
- `/start_training` - Begin training session
- `/submit_answer` - Process training answers
- `/get_statistic` - Get user statistics
- `/get_errors` - Get error analysis

## Deployment

The application is designed to run on Streamlit Cloud. Ensure all environment variables are set in the Streamlit Cloud secrets.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.