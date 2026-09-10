# Submission readiness and evaluation

## Scope implemented

- PDF, UTF-8 text-file, and pasted-note input with clear size limits.
- Persistent per-note summaries, key concepts, structured flashcards, and quizzes in SQLite.
- Saved-note selection and search; quiz history with explanations.
- Interactive answer reveal, card navigation, quiz progress, and incomplete-answer checks.
- Per-note score-based revision recommendations, monthly calendar, overdue labels, review completion, and rescheduling.
- Salted password hashing with backward-compatible sign-in migration; ownership checks.
- Study record export excluding credentials.

## Explain accurately in the report and viva

Generative AI creates learning content. The retention planner uses an exponential formula and hand-selected score thresholds. It is not a trained machine-learning model and has no measured predictive accuracy. At day zero its estimate is 100% even for a low quiz score. The score changes the rate of decline. A completed review resets elapsed time and its self-assessment chooses the next interval.

The current chart uses Streamlit's built-in chart support. If the synopsis names Plotly, update the implementation chapter to reflect the actual library. RAG, mobile notifications, handwriting recognition, and empirical retention-model training remain future work.

## Evaluation to include in submission

Automated tests verify workflow correctness, not educational effectiveness. For manual evaluation, use the three included sample PDFs and record whether definitions in summaries match the source, questions have one defensible answer, explanations are supported, and saved records reopen correctly. Record elapsed time for each real AI call without claiming a guaranteed response time.

For a learning-effectiveness study, a separate consented longitudinal evaluation with delayed recall and a comparison condition would be required. Do not infer improved long-term retention from passing software tests.

## Deployment limitations

SQLite remains local to the service. The user chose not to add an external database; cloud file persistence is therefore not guaranteed. Keep downloaded exports. AI availability and quotas depend on the configured account. OCR is not included.

## Verification on 11 September 2026

The initial upgrade suite passed 16 automated tests. Live Gemini requests using a synthetic database-study paragraph succeeded locally: summary 14.4 s, flashcards 13.4 s, quiz 13.4 s, and keywords 11.7 s. These are single-run observations, not benchmarks or guaranteed hosting latency. Hosted credentials require separate verification.

