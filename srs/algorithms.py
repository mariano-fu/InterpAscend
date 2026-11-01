"""
SM-2 Spaced Repetition Algorithm Implementation

This module implements the SM-2 algorithm for spaced repetition learning,
originally developed by Piotr Wozniak for SuperMemo.

The algorithm adjusts the interval between reviews based on the user's
performance, optimizing long-term retention.
"""

import math
from datetime import datetime, timedelta
from typing import NamedTuple, Optional
from django.utils import timezone


class SM2State(NamedTuple):
    """
    Represents the current state of a card in the SM-2 algorithm.
    
    Attributes:
        ease_factor: The ease factor (EF) - how easy the card is to remember
        interval: Days until the next review
        repetitions: Number of successful repetitions in a row
        due: When the card is due for review
    """
    ease_factor: float
    interval: int
    repetitions: int
    due: datetime


class SM2Result(NamedTuple):
    """
    Result of applying the SM-2 algorithm to a card review.
    
    Attributes:
        new_state: The updated SM2State after the review
        was_successful: Whether the review was considered successful (quality >= 3)
        interval_changed: Whether the interval was modified
    """
    new_state: SM2State
    was_successful: bool
    interval_changed: bool


def sm2_update(
    current_state: SM2State,
    quality: int,
    reviewed_at: Optional[datetime] = None
) -> SM2Result:
    """
    Update the SM-2 state based on a review quality rating.
    
    Args:
        current_state: Current SM2State of the card
        quality: Quality of the response (0-5)
                0 = complete blackout
                1 = incorrect response; the correct one remembered
                2 = incorrect response; where the correct one seemed easy to recall
                3 = correct response recalled with serious difficulty
                4 = correct response after a hesitation
                5 = perfect response
        reviewed_at: When the review took place (defaults to now)
    
    Returns:
        SM2Result containing the new state and metadata
    
    Raises:
        ValueError: If quality is not in range 0-5
    """
    if not 0 <= quality <= 5:
        raise ValueError(f"Quality must be between 0 and 5, got {quality}")
    
    if reviewed_at is None:
        reviewed_at = timezone.now()
    
    # Extract current values
    ease_factor = current_state.ease_factor
    interval = current_state.interval
    repetitions = current_state.repetitions
    
    # Track if this was a successful review
    was_successful = quality >= 3
    
    # Track if interval changed
    old_interval = interval
    
    if quality < 3:
        # Failed review - reset repetitions and set immediate reappearance
        repetitions = 0
        interval = 0  # Immediate reappearance
    else:
        # Successful review - handle learning phase
        if repetitions == 0:
            # First time seeing this card or after failure - learning phase
            if quality == 3:  # Hard - 1 minute for same-session reappearance
                interval = 1.0 / 1440.0  # 1 minute as fraction of day
                repetitions = 0  # Stay in learning phase
            elif quality == 4:  # Good - 3 minutes for same-session reappearance
                interval = 3.0 / 1440.0  # 3 minutes as fraction of day
                repetitions = 0  # Stay in learning phase
            else:  # Easy (quality 5)
                interval = 4  # Graduate to 4 days
                repetitions = 1
        elif repetitions == 1:
            # Second successful review
            if quality == 3:  # Hard
                interval = 1  # 1 day
                repetitions = 2
            else:  # Good or Easy
                interval = 6  # 6 days
                repetitions = 2
        else:
            # Mature card (repetitions >= 2) - use SM-2 algorithm
            repetitions += 1
            interval = math.ceil(interval * ease_factor)
    
    # Update ease factor based on quality
    # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    
    # Ensure ease factor doesn't go below 1.3 (minimum threshold)
    ease_factor = max(1.3, ease_factor)
    
    # Calculate due date
    due = reviewed_at + timedelta(days=interval)
    
    # Create new state
    new_state = SM2State(
        ease_factor=round(ease_factor, 2),
        interval=interval,
        repetitions=repetitions,
        due=due
    )
    
    return SM2Result(
        new_state=new_state,
        was_successful=was_successful,
        interval_changed=(interval != old_interval)
    )


def create_initial_state(created_at: Optional[datetime] = None) -> SM2State:
    """
    Create the initial SM-2 state for a new card.
    
    Args:
        created_at: When the card was created (defaults to now)
    
    Returns:
        Initial SM2State with default values
    """
    if created_at is None:
        created_at = timezone.now()
    
    return SM2State(
        ease_factor=2.5,  # Default ease factor
        interval=0,       # New cards are due immediately
        repetitions=0,    # No successful repetitions yet
        due=created_at    # Due immediately
    )


def next_due_date(current_date: datetime, days: int) -> datetime:
    """
    Calculate the next due date given a current date and interval in days.
    
    Args:
        current_date: The reference date
        days: Number of days to add
    
    Returns:
        The calculated due date
    """
    return current_date + timedelta(days=days)


def get_interval_description(interval: float) -> str:
    """
    Get a human-readable description of an interval.

    Args:
        interval: Interval in days (float). Values between 0 and 1 represent minutes.

    Returns:
        Human-readable description
    """
    if interval == 0:
        return "Due now"

    # Minute-based learning intervals (fractional day)
    if 0 < interval < 1:
        minutes = math.ceil(interval * 1440)  # always at least 1 minute
        if minutes == 1:
            return "1 minute"
        return f"{minutes} minutes"

    # Day-based intervals
    days = int(round(interval))
    if days == 1:
        return "1 day"
    elif days < 7:
        return f"{days} days"
    elif days < 30:
        weeks = days // 7
        remaining_days = days % 7
        if weeks == 1:
            if remaining_days == 0:
                return "1 week"
            else:
                return f"1 week, {remaining_days} day{'s' if remaining_days > 1 else ''}"
        else:
            if remaining_days == 0:
                return f"{weeks} weeks"
            else:
                return f"{weeks} weeks, {remaining_days} day{'s' if remaining_days > 1 else ''}"
    elif days < 365:
        months = days // 30
        remaining_days = days % 30
        if months == 1:
            if remaining_days == 0:
                return "1 month"
            else:
                return f"1 month, {remaining_days} day{'s' if remaining_days > 1 else ''}"
        else:
            if remaining_days == 0:
                return f"{months} months"
            else:
                return f"{months} months, {remaining_days} day{'s' if remaining_days > 1 else ''}"
    else:
        years = days // 365
        remaining_days = days % 365
        if years == 1:
            if remaining_days == 0:
                return "1 year"
            else:
                return f"1 year, {remaining_days} day{'s' if remaining_days > 1 else ''}"
        else:
            if remaining_days == 0:
                return f"{years} years"
            else:
                return f"{years} years, {remaining_days} day{'s' if remaining_days > 1 else ''}"


def calculate_retention_rate(ease_factor: float) -> float:
    """
    Estimate retention rate based on ease factor.
    This is an approximation based on SM-2 research.
    
    Args:
        ease_factor: The current ease factor
    
    Returns:
        Estimated retention rate as a percentage (0-100)
    """
    # This is a simplified estimation
    # Higher ease factor = higher retention rate
    # EF of 1.3 ≈ 70% retention, EF of 2.5 ≈ 90% retention
    if ease_factor <= 1.3:
        return 70.0
    elif ease_factor >= 2.5:
        return min(95.0, 70.0 + (ease_factor - 1.3) * 20.0)
    else:
        # Linear interpolation between 1.3 and 2.5
        return 70.0 + (ease_factor - 1.3) * ((90.0 - 70.0) / (2.5 - 1.3))


def get_quality_description(quality: int) -> str:
    """
    Get a human-readable description of a quality rating.
    
    Args:
        quality: Quality rating (0-5)
    
    Returns:
        Human-readable description
    """
    descriptions = {
        0: "Complete blackout - no memory of the answer",
        1: "Incorrect response, but correct answer was easy to recall",
        2: "Incorrect response, correct answer was difficult to recall",
        3: "Correct response with serious difficulty",
        4: "Correct response after hesitation",
        5: "Perfect response - immediate and confident"
    }
    return descriptions.get(quality, "Unknown quality level")


def simulate_learning_curve(
    initial_state: SM2State,
    quality_sequence: list[int],
    start_date: Optional[datetime] = None
) -> list[SM2State]:
    """
    Simulate a learning curve by applying a sequence of quality ratings.
    Useful for testing and demonstration purposes.
    
    Args:
        initial_state: Starting SM2State
        quality_sequence: List of quality ratings to apply
        start_date: Starting date for simulation (defaults to now)
    
    Returns:
        List of SM2States showing the progression
    """
    if start_date is None:
        start_date = timezone.now()
    
    states = [initial_state]
    current_state = initial_state
    current_date = start_date
    
    for quality in quality_sequence:
        # Simulate reviewing at the due date
        current_date = current_state.due
        result = sm2_update(current_state, quality, current_date)
        current_state = result.new_state
        states.append(current_state)
    
    return states


# Quality rating constants for easier use
QUALITY_BLACKOUT = 0
QUALITY_INCORRECT_EASY = 1
QUALITY_INCORRECT_HARD = 2
QUALITY_CORRECT_HARD = 3
QUALITY_CORRECT_HESITATION = 4
QUALITY_PERFECT = 5

# Ease factor bounds
MIN_EASE_FACTOR = 1.3
DEFAULT_EASE_FACTOR = 2.5
MAX_EASE_FACTOR = 5.0