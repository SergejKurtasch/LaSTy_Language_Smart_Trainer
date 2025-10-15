# **Final Technical Specification (TS) - Lasty: Language Smart Trainer (MVP)**

**Version:** `1.0`

### **0. Project Goal & Tech Stack**

| Parameter | Value |
| :--- | :--- |
| **Goal** | To create a web application for language learning practice using AI for sentence generation, user progress tracking, and error analysis. |
| **Platform** | Streamlit Cloud |
| **Database** | Supabase / Cloud SQL (for users, words, and errors) |

---

### **1. User Authentication**

* **Registration/Login**: Simple local authentication (login + password).
* **Password Storage**: Passwords must be stored as hashes. Password recovery via e-mail is not included in the MVP. Admins will reset passwords manually.
* **Session**: Persistent for 7 days. Manual logout clears the session cookies.
* **Roles**: An admin role will be implemented via an `is_admin` field in the `users` table (default `FALSE`).

**Table: `users`**

| Field | Type | Description |
| :--- | :--- | :--- |
| **user\_id** (PK) | UUID / serial | Unique user identifier |
| login | text | User's login name |
| password\_hash | text | Hashed password |
| native\_language | text | User's native language (English, Deutsch, Español, Russian, Ukrainian) |
| learning\_languages | array/text[] | List of languages being learned |
| preferred\_topics | array/text[] | Topics of interest (Business, Travel, Hobbies, IT) |
| interface\_language | text | Interface language (defaults to native language or English) |
| is\_admin | boolean | Administrator role |

---

### **2. Word Base Import & Structure**

* **Import Format**: CSV/TXT (2 columns: native language + target language), without a header. Supports phrases.
* **Language Validation**: Use FastText to validate that each word pair belongs to the selected languages.
* **Import Error Handling**: Invalid pairs are saved to a temporary list for user review. If errors exceed 20%, the user is prompted to "Continue" or "Cancel" the import.
* **Duplicate Handling**: Duplicates are identified using `trim` + `lower`. Duplicates are skipped to preserve the progress of existing words.

**Table: `word_pairs`**

| Field | Type | Description |
| :--- | :--- | :--- |
| **word\_id** (PK) | UUID/serial | Unique word ID |
| **user\_id** (FK) | UUID | The user who owns the word |
| native\_word | text | The word/phrase in the native language |
| target\_word | text | The translation in the target language (Keyword) |
| progress | integer | Memorization percentage (0-100) |
| last\_training\_date | date | Date of the last training session |
| next\_training\_date | date | Next training date based on the Ebbinghaus algorithm |
| language | text | The target language being learned |

---

### **3. Progress Algorithm & Word Selection**

#### **Training Update Logic**

* ✅ **On Correct Answer:**
    * `progress = min(100, progress + 20)`
    * `last_training_date = today`
    * `next_training_date` is determined by the **new** `progress` value from the Intervals Table below.

* ❌ **On Incorrect Answer:**
    * `progress = max(0, progress - 40)`
    * `last_training_date = today`
    * `next_training_date = today` (Goal: repeat the word on the same day).

* 🧠 **On Morphological Error (meaning is correct):**
    * `progress` remains unchanged.
    * `next_training_date` remains unchanged.
    * The user is notified of the error, but the answer is accepted.

* **On Synonym Answer:**
    * The answer is accepted as correct, but `progress` does not change.
    * A message is shown to the user: "Great! That's a synonym. We are practicing the word '{target\_word}'."

#### **Ebbinghaus Intervals Table**
*The interval is determined by the `progress` value **AFTER** it has been updated.*

| `progress` Range (after update) | Interval Until Next Training | Stage Name |
| :--- | :--- | :--- |
| 0–19 | +1 day | Initial Memorization |
| 20–39 | +3 days | First Repetition |
| 40–59 | +7 days | Medium Stage |
| 60–79 | +14 days | Consolidation |
| 80–99 | +30 days | Control Repetition |
| 100 | +120 days | Long-term Retention |

#### **Word Selection for Training**
*Words are selected until the training session limit (1, 5, 10, or 20 words) is reached.*

1.  **Priority 1**: Select only words where `next_training_date <= today`.
2.  **Priority 2**: If there are many such words, select from them **randomly**.
3.  **Priority 3**: If there are no words with a past-due training date, select **any other words** randomly for the session.

---

### **4. Training Cycle**

* **Task Types**:
    1.  Full translation input.
    2.  Multiple Choice (select from 3 options).
    3.  Fill in the blank (insert the keyword into a sentence).

* **Task Alternation (Weighted Choice)**: The probability of a task type depends on the word's `progress`:
    * **Low Progress (0-40%)**: Higher probability of "Multiple Choice".
    * **Medium Progress (41-70%)**: Higher probability of "Fill in the blank".
    * **High Progress (71-100%)**: Higher probability of "Full translation input".

* **Sentence Generation (AI)**: The AI generates a sentence in the target language that includes the `target_word`, considers the user's `preferred_topics`, and incorporates a grammatical structure the user often makes mistakes with (from the `errors` table). The sentence translation is shown to the user for context.

* **Answer Verification**: The check must account for morphology (different word forms) and synonyms.

---

### **5. User Error Tracking**

**Table: `errors`**

| Field | Type | Description |
| :--- | :--- | :--- |
| **error\_id** (PK) | serial / UUID | Unique error ID |
| **user\_id** (FK) | UUID | The user who made the error |
| language | text | The target language |
| description | text | A unified error code/category (e.g., "Grammar: Article omission", "Verb: Wrong tense") |
| count | integer | The number of times this specific error has been made |

**Update Logic**:
1.  When a user makes a mistake, the AI analyzes it and assigns a unified `description`.
2.  The system searches for an existing record with the same `user_id`, `language`, and `description`.
3.  If a record is found, its `count` is incremented (`count++`).
4.  If not found, a new record is created with `count = 1`.

---

### **6. LLM / API**

* **API**: Use the OpenAI API.
* **Models**:
    * **Sentence Generation** (Cost-effective): `GPT-4o-mini` (or similar).
    * **Error Explanation & Classification** (Accurate): `GPT-4o` (or similar).
* **Caching**: Caching for LLM responses (TTL cache) will not be implemented at this stage.
* **Tracking**: Implement token usage tracking per user (доступ через код и Supabase).

---

### **7. API Endpoints (REST / Streamlit internal API)**

* `/register`, `/login`, `/logout`
* `/upload_words`, `/delete_word`, `/get_words`
* `/start_training` (includes word selection logic)
* `/submit_answer` (includes answer verification, progress update, and error analysis)
* `/get_statistic`
* `/get_errors`
---

### **8. Additional Clarifications**

#### **Security and Validation:**
* Login/password restrictions: none
* Password complexity validation: not required
* Protection against SQL injection and XSS: not implemented in MVP

#### **Performance:**
* Maximum number of users: 50
* Indexes for optimization: created where possible in Supabase
* Scalability: not critical for MVP

#### **User Interface:**
* File upload: standard button (not drag & drop)
* Progress notifications: not required
* Mobile adaptation: required

#### **Integration with FastText:**
* Model: Multi-lingual word vectors via API
* Cloud Streamlit operation with link access

#### **Error Handling:**
* OpenAI API unavailable: show a placeholder
* AI cannot generate a sentence: suggest a translation of a single key word

#### **Administrative Functions:**
* Admin functions removed from user interface
* Access to statistics only via code and Supabase

#### **Testing:**
* Unit testing: not planned for MVP

---