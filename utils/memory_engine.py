import math
from datetime import date, timedelta


def calculate_retention(days_since_study, quiz_score):
    """
    Estimates retention using a personalised forgetting-curve model.
    A stronger quiz score creates a slower memory decline.
    """
    quiz_score = max(0, min(quiz_score, 100))

    memory_strength_days = 2 + (quiz_score / 100) * 12

    retention = 100 * math.exp(
        -days_since_study / memory_strength_days
    )

    return round(retention, 1)


def get_revision_interval(quiz_score):
    """Returns the recommended number of days until revision."""
    if quiz_score >= 85:
        return 7
    if quiz_score >= 70:
        return 4
    if quiz_score >= 50:
        return 2
    return 1


def get_revision_date(quiz_score):
    """Returns the next recommended revision date."""
    interval = get_revision_interval(quiz_score)
    return date.today() + timedelta(days=interval)