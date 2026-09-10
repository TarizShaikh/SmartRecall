"""Quiz scoring is independent from UI and requires a complete validated attempt."""
from utils.gemini_helper import validate_quiz


def evaluate_quiz(questions, answers):
    validate_quiz(questions)
    if len(answers)!=len(questions) or any(answer is None for answer in answers):
        raise ValueError('Answer every question before submitting.')
    if any(answer not in q['options'] for q,answer in zip(questions,answers)):
        raise ValueError('An answer is not one of the available choices.')
    details = [dict(question=q['question'], selected=answer, answer=q['answer'],
                    explanation=q['explanation'], correct=answer==q['answer']) for q,answer in zip(questions,answers)]
    correct = sum(d['correct'] for d in details)
    return dict(score=round(correct/len(questions)*100,1), correct=correct, total=len(questions), details=details)
