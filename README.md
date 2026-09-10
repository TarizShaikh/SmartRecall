# SmartRecall

A Streamlit study assistant with saved notes, AI summaries and key concepts, interactive flashcards, validated quizzes, and a rule-based revision calendar.

## Run locally

Use Python 3.13 or newer. Install `requirements.txt`, configure `GEMINI_API_KEY` in `.env`, and run:

```text
python -m streamlit run app.py
```

`GEMINI_MODEL` optionally overrides the default model. Hosted deployments read the same variables from Streamlit Secrets. Never commit secrets or the study database.

## Study workflow

1. Add a PDF, UTF-8 TXT file, or pasted text (80 to 40,000 characters; files at most 10 MB).
2. Save and open a note in the library. Saved material is tied to that exact note.
3. Generate a summary and key concepts, then practise revealable flashcards.
4. Complete every quiz question. Results, explanations, and history are saved once per attempt.
5. Create a revision plan using the latest quiz for the selected note.
6. Mark a review completed, assess recall, and get a new scheduled review.
7. Export your study records from Profile.

## Storage and authentication

SQLite is retained. `SMARTRECALL_DATABASE_PATH` can point to persistent storage. On hosting without persistent storage, keep exports of important records. This update does not provision a cloud database.

Schema upgrades add columns and tables without deleting existing records. New passwords use PBKDF2-HMAC-SHA256 with a random salt and 600,000 iterations. Legacy SHA-256 hashes upgrade after a successful sign-in. All note, material, history, and revision operations check account ownership.

## Retention model and limits

The curve is an illustrative rule-based estimate: `R = 100 * exp(-days / S)`, where `S = 2 + 12 * score / 100`. Review intervals are 1, 2, 4, or 7 days based on score thresholds. These parameters are not fitted to a study dataset and must not be presented as validated prediction accuracy. Completed reviews reset the last-study timestamp. Self-reported recall sets the next interval but is not counted as a quiz attempt.

AI-generated content may be inaccurate. Uploaded notes are sent to the configured Gemini service when generation is requested. Scanned/image-only PDFs require external OCR. Generation has bounded timeouts and retries; saved material is reused until explicitly regenerated. No claim of measured learning improvement is made.

## Tests

```text
python -m unittest discover -s tests -v
```

Tests use isolated temporary databases and stubbed AI output. They cover ownership, password migration, idempotent submissions, note switching, quiz validation, revision completion, and real Streamlit page interactions. Live AI checks are separate and depend on configured provider access.
