import os

import json
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")


def generate_summary(note_text):
    """Creates a clear student-friendly summary of uploaded notes."""
    if not API_KEY:
        raise ValueError(
            "Gemini API key not found. Check that your .env file is saved."
        )

    from google import genai
    client = genai.Client(api_key=API_KEY)

    prompt = f"""
    You are SmartRecall, an academic study assistant.

    Summarise the following study notes in simple, clear language.
    Use headings and bullet points.
    Include the most important concepts and definitions.
    Do not add information that is not in the notes.

    STUDY NOTES:
    {note_text[:12000]}
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )

    return response.text

def generate_flashcards(note_text):
    """Creates five question-and-answer flashcards from the notes."""
    if not API_KEY:
        raise ValueError(
            "Gemini API key not found. Check that your .env file is saved."
        )

    from google import genai
    client = genai.Client(api_key=API_KEY)

    prompt = f"""
    You are SmartRecall, an academic study assistant.

    Create exactly 5 concise flashcards from the study notes below.

    Use this format for every flashcard:

    Question: ...
    Answer: ...

    Only use information from the notes.

    STUDY NOTES:
    {note_text[:12000]}
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )

    return response.text

def generate_quiz(note_text):
    """Creates five multiple-choice questions from the uploaded notes."""
    if not API_KEY:
        raise ValueError(
            "Gemini API key not found. Check that your .env file is saved."
        )

    from google import genai
    client = genai.Client(api_key=API_KEY)

    prompt = f"""
    You are SmartRecall, an academic study assistant.

    Create exactly 5 multiple-choice questions from the study notes below.

    Return ONLY valid JSON. Do not use Markdown or code fences.

    Use this exact format:
    [
      {{
        "question": "Question text",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": "Option A"
      }}
    ]

    Rules:
    - Each question must have four options.
    - The answer must be one of the four options exactly.
    - Use only information from the notes.

    STUDY NOTES:
    {note_text[:12000]}
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )

    quiz_text = response.text.strip()
    quiz_text = quiz_text.replace("```json", "").replace("```", "").strip()

    return json.loads(quiz_text)
