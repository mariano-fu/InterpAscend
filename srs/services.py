"""
SRS Service Functions

This module provides high-level service functions for the Spaced Repetition System,
including card retrieval, user card initialization, and review processing.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.utils import timezone
import random

logger = logging.getLogger(__name__)

from .models import Category, Deck, DeckItem, UserCard, ReviewLog
from .algorithms import (
    sm2_update, create_initial_state, SM2State, SM2Result,
    get_interval_description, calculate_retention_rate
)


def get_due_usercards(
    user: User,
    category_id: Optional[int] = None,
    limit: int = 50,
    include_new: bool = True
) -> List[UserCard]:
    """
    Get cards that are due for review for a specific user.
    Prioritizes recently failed cards (interval=1, repetitions=0) to ensure they reappear immediately.
    
    Args:
        user: The user to get cards for
        category_id: Optional category to filter by
        limit: Maximum number of cards to return
        include_new: Whether to include new cards (never reviewed)
    
    Returns:
        List of UserCard objects that are due for review
    """
    # DEBUG LOGGING
    now = timezone.now()
    logger.info(f"🔍 CARD RETRIEVAL DEBUG - User: {user.username}, Category: {category_id}, Limit: {limit}, Time: {now}")
    
    base_queryset = UserCard.objects.filter(
        user=user,
        suspended=False,
        deck_item__is_active=True,
        deck_item__deck__is_active=True,
        deck_item__deck__category__is_active=True
    ).select_related(
        'deck_item__deck__category',
        'deck_item__content_type'
    ).prefetch_related(
        'deck_item__term_content_object'
    )
    
    # Filter by category if specified
    if category_id:
        base_queryset = base_queryset.filter(deck_item__deck__category_id=category_id)
    
    # DEBUG: Count total cards before filtering
    total_cards = base_queryset.count()
    logger.info(f"🔍 TOTAL CARDS in category: {total_cards}")
    
    # PRIORITY 1: Recently failed cards and learning cards
    # These include immediate (0), fractional minute intervals, and short day intervals (1)
    failed_cards = list(base_queryset.filter(
        Q(interval__lte=1),  # Include immediate (0), fractional minutes, and short (1) intervals
        repetitions=0,
        due__lte=now,
        last_reviewed__isnull=False  # Must have been reviewed (not new cards)
    ).order_by('-last_reviewed'))  # Most recently failed first
    
    logger.info(f"🔍 FAILED CARDS (priority): {len(failed_cards)}")
    for card in failed_cards[:3]:  # Log first 3
        logger.info(f"🔍 FAILED CARD - ID: {card.deck_item.id}, Due: {card.due}, Last Reviewed: {card.last_reviewed}")
    
    # PRIORITY 2: Other due cards (including new cards if requested)
    other_due_filter = Q(due__lte=now)
    if include_new:
        other_due_filter |= Q(last_reviewed__isnull=True)
    
    # Exclude the failed cards we already got
    failed_card_ids = [card.id for card in failed_cards]
    other_due_cards = list(base_queryset.filter(other_due_filter).exclude(
        id__in=failed_card_ids
    ).order_by('?')[:limit * 2])  # Get more than needed for randomization
    
    logger.info(f"🔍 OTHER DUE CARDS: {len(other_due_cards)}")
    
    # Combine cards with failed cards taking priority
    all_cards = failed_cards + other_due_cards
    
    # Shuffle only the non-failed cards to maintain failed card priority
    if len(other_due_cards) > 1:
        random.shuffle(other_due_cards)
        all_cards = failed_cards + other_due_cards
    
    # Return the requested number of cards
    final_cards = all_cards[:limit]
    logger.info(f"🔍 RETURNING {len(final_cards)} cards for study ({len([c for c in final_cards if c.interval == 1 and c.repetitions == 0 and c.last_reviewed])} failed cards prioritized)")
    
    return final_cards


def ensure_usercards_exist(user: User, deck: Deck) -> int:
    """
    Ensure UserCard objects exist for all active DeckItems in a deck for a user.
    Creates UserCard objects for any missing cards.
    
    Args:
        user: The user to create cards for
        deck: The deck to create cards for
    
    Returns:
        Number of UserCard objects created
    """
    created_count = 0
    
    # Get all active deck items that don't have user cards yet
    deck_items = DeckItem.objects.filter(
        deck=deck,
        is_active=True
    ).exclude(
        user_cards__user=user
    )
    
    # Create UserCard objects for missing items
    user_cards_to_create = []
    for deck_item in deck_items:
        initial_state = create_initial_state()
        user_card = UserCard(
            user=user,
            deck_item=deck_item,
            ease_factor=initial_state.ease_factor,
            interval=initial_state.interval,
            repetitions=initial_state.repetitions,
            due=initial_state.due
        )
        user_cards_to_create.append(user_card)
    
    if user_cards_to_create:
        UserCard.objects.bulk_create(user_cards_to_create)
        created_count = len(user_cards_to_create)
    
    return created_count


def review_card(
    user: User,
    deck_item_id: int,
    quality: int,
    reviewed_at: Optional[datetime] = None,
    latency_ms: Optional[int] = None,
    study_session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a card review and update the user's progress.
    
    Args:
        user: The user reviewing the card
        deck_item_id: ID of the DeckItem being reviewed
        quality: Quality rating (0-5)
        reviewed_at: When the review took place (defaults to now)
        latency_ms: Time taken to answer in milliseconds
        study_session_id: ID to group reviews from the same session
    
    Returns:
        Dictionary containing review results and updated card state
    
    Raises:
        UserCard.DoesNotExist: If the user card doesn't exist
        ValueError: If quality is invalid
    """
    if reviewed_at is None:
        reviewed_at = timezone.now()
    
    if study_session_id is None:
        study_session_id = str(uuid.uuid4())[:8]
    
    # DEBUG LOGGING
    logger.info(f"🔍 REVIEW DEBUG - User: {user.username}, DeckItem: {deck_item_id}, Quality: {quality}")
    
    try:
        with transaction.atomic():
            # Get the user card
            user_card = UserCard.objects.select_for_update().get(
                user=user,
                deck_item_id=deck_item_id
            )
            
            # DEBUG: Log current state
            logger.info(f"🔍 BEFORE REVIEW - EF: {user_card.ease_factor}, Interval: {user_card.interval}, Reps: {user_card.repetitions}, Due: {user_card.due}")
            
            # Create current SM-2 state from user card
            current_state = SM2State(
                ease_factor=user_card.ease_factor,
                interval=user_card.interval,
                repetitions=user_card.repetitions,
                due=user_card.due
            )
            
            # Apply SM-2 algorithm
            result = sm2_update(current_state, quality, reviewed_at)
            new_state = result.new_state
            
            # DEBUG: Log new state
            logger.info(f"🔍 AFTER SM-2 - EF: {new_state.ease_factor}, Interval: {new_state.interval}, Reps: {new_state.repetitions}, Due: {new_state.due}")
            
            # Update user card with new state
            user_card.ease_factor = new_state.ease_factor
            user_card.interval = new_state.interval
            user_card.repetitions = new_state.repetitions
            user_card.due = new_state.due
            user_card.last_reviewed = reviewed_at
            
            # Update lapse count if failed
            if not result.was_successful:
                user_card.lapses += 1
                logger.info(f"🔍 CARD FAILED - Lapses now: {user_card.lapses}, Should reappear immediately")
            
            user_card.save()
            
            # Create review log entry
            review_log = ReviewLog.objects.create(
                user=user,
                deck_item_id=deck_item_id,
                reviewed_at=reviewed_at,
                quality=quality,
                ease_factor=new_state.ease_factor,
                interval=new_state.interval,
                repetitions=new_state.repetitions,
                latency_ms=latency_ms,
                study_session_id=study_session_id
            )
            
            return {
                'success': True,
                'user_card': user_card,
                'review_log': review_log,
                'was_successful': result.was_successful,
                'interval_changed': result.interval_changed,
                'next_due': new_state.due,
                'interval_description': get_interval_description(new_state.interval),
                'retention_estimate': calculate_retention_rate(new_state.ease_factor)
            }
            
    except UserCard.DoesNotExist:
        # Try to create the user card if it doesn't exist
        try:
            deck_item = DeckItem.objects.get(id=deck_item_id, is_active=True)
            ensure_usercards_exist(user, deck_item.deck)
            
            # Retry the review
            return review_card(
                user, deck_item_id, quality, reviewed_at, latency_ms, study_session_id
            )
        except DeckItem.DoesNotExist:
            raise ValueError(f"DeckItem {deck_item_id} does not exist or is not active")


def get_user_study_stats(user: User, category_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get comprehensive study statistics for a user.
    
    Args:
        user: The user to get stats for
        category_id: Optional category to filter by
    
    Returns:
        Dictionary containing various study statistics
    """
    # Base querysets
    user_cards_qs = UserCard.objects.filter(user=user)
    review_logs_qs = ReviewLog.objects.filter(user=user)
    
    if category_id:
        user_cards_qs = user_cards_qs.filter(deck_item__deck__category_id=category_id)
        review_logs_qs = review_logs_qs.filter(deck_item__deck__category_id=category_id)
    
    # Basic counts
    total_cards = user_cards_qs.count()
    total_reviews = review_logs_qs.count()
    
    # Due cards
    now = timezone.now()
    due_cards = user_cards_qs.filter(
        due__lte=now,
        suspended=False,
        deck_item__is_active=True
    ).count()
    
    # New cards (never reviewed)
    new_cards = user_cards_qs.filter(last_reviewed__isnull=True).count()
    
    # Cards by maturity
    mature_cards = user_cards_qs.filter(interval__gte=21).count()  # 3+ weeks
    young_cards = user_cards_qs.filter(interval__lt=21, interval__gt=0).count()
    
    # Average ease factor
    avg_ease_factor = user_cards_qs.aggregate(
        avg_ef=Avg('ease_factor')
    )['avg_ef'] or 2.5
    
    # Recent activity (last 7 days)
    week_ago = now - timedelta(days=7)
    recent_reviews = review_logs_qs.filter(reviewed_at__gte=week_ago).count()
    
    # Success rate (last 30 days)
    month_ago = now - timedelta(days=30)
    recent_review_logs = review_logs_qs.filter(reviewed_at__gte=month_ago)
    successful_reviews = recent_review_logs.filter(quality__gte=3).count()
    total_recent_reviews = recent_review_logs.count()
    
    success_rate = 0
    if total_recent_reviews > 0:
        success_rate = (successful_reviews / total_recent_reviews) * 100
    
    # Study streak (consecutive days with reviews)
    study_streak = calculate_study_streak(user)
    
    # Next review times
    next_reviews = user_cards_qs.filter(
        suspended=False,
        deck_item__is_active=True,
        due__gt=now
    ).order_by('due')[:5]
    
    return {
        'total_cards': total_cards,
        'total_reviews': total_reviews,
        'due_cards': due_cards,
        'new_cards': new_cards,
        'mature_cards': mature_cards,
        'young_cards': young_cards,
        'average_ease_factor': round(avg_ease_factor, 2),
        'recent_reviews': recent_reviews,
        'success_rate': round(success_rate, 1),
        'study_streak': study_streak,
        'next_reviews': [
            {
                'deck_item': card.deck_item,
                'due': card.due,
                'interval_description': get_interval_description(card.days_until_due() or 0)
            }
            for card in next_reviews
        ],
        'retention_estimate': round(calculate_retention_rate(avg_ease_factor), 1)
    }


def calculate_study_streak(user: User) -> int:
    """
    Calculate the current study streak for a user (consecutive days with reviews).
    
    Args:
        user: The user to calculate streak for
    
    Returns:
        Number of consecutive days with reviews
    """
    today = timezone.now().date()
    streak = 0
    current_date = today
    
    # Check each day going backwards
    while True:
        # Check if user has reviews on this date
        has_reviews = ReviewLog.objects.filter(
            user=user,
            reviewed_at__date=current_date
        ).exists()
        
        if has_reviews:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            # If today has no reviews, streak is 0
            # If any other day has no reviews, streak ends
            if current_date == today:
                streak = 0
            break
        
        # Prevent infinite loop (max 365 days)
        if streak >= 365:
            break
    
    return streak


def get_category_progress(user: User) -> List[Dict[str, Any]]:
    """
    Get progress statistics for each category the user is studying.
    
    Args:
        user: The user to get progress for
    
    Returns:
        List of dictionaries containing category progress data
    """
    categories = Category.objects.filter(
        is_active=True,
        decks__deck_items__user_cards__user=user
    ).distinct().annotate(
        total_cards=Count('decks__deck_items__user_cards', distinct=True),
        due_cards=Count(
            'decks__deck_items__user_cards',
            filter=Q(
                decks__deck_items__user_cards__due__lte=timezone.now(),
                decks__deck_items__user_cards__suspended=False
            ),
            distinct=True
        )
    )
    
    progress_data = []
    for category in categories:
        stats = get_user_study_stats(user, category.id)
        progress_data.append({
            'category': category,
            'total_cards': stats['total_cards'],
            'due_cards': stats['due_cards'],
            'success_rate': stats['success_rate'],
            'average_ease_factor': stats['average_ease_factor'],
            'recent_reviews': stats['recent_reviews']
        })
    
    return progress_data


def suspend_card(user: User, deck_item_id: int, suspended: bool = True) -> bool:
    """
    Suspend or unsuspend a card for a user.
    
    Args:
        user: The user
        deck_item_id: ID of the DeckItem
        suspended: Whether to suspend (True) or unsuspend (False) the card
    
    Returns:
        True if successful, False if card not found
    """
    try:
        user_card = UserCard.objects.get(user=user, deck_item_id=deck_item_id)
        user_card.suspended = suspended
        user_card.save()
        return True
    except UserCard.DoesNotExist:
        return False


def reset_card_progress(user: User, deck_item_id: int) -> bool:
    """
    Reset a card's progress back to initial state.
    
    Args:
        user: The user
        deck_item_id: ID of the DeckItem
    
    Returns:
        True if successful, False if card not found
    """
    try:
        user_card = UserCard.objects.get(user=user, deck_item_id=deck_item_id)
        initial_state = create_initial_state()
        
        user_card.ease_factor = initial_state.ease_factor
        user_card.interval = initial_state.interval
        user_card.repetitions = initial_state.repetitions
        user_card.due = initial_state.due
        user_card.lapses = 0
        user_card.last_reviewed = None
        user_card.save()
        
        return True
    except UserCard.DoesNotExist:
        return False


def get_study_session_summary(study_session_id: str) -> Dict[str, Any]:
    """
    Get a summary of a completed study session.
    
    Args:
        study_session_id: The study session ID
    
    Returns:
        Dictionary containing session summary data
    """
    reviews = ReviewLog.objects.filter(study_session_id=study_session_id)
    
    if not reviews.exists():
        return {'error': 'Study session not found'}
    
    total_reviews = reviews.count()
    successful_reviews = reviews.filter(quality__gte=3).count()
    failed_reviews = total_reviews - successful_reviews
    
    # Quality distribution
    quality_counts = {}
    for i in range(6):
        quality_counts[i] = reviews.filter(quality=i).count()
    
    # Average response time
    avg_latency = reviews.exclude(latency_ms__isnull=True).aggregate(
        avg=Avg('latency_ms')
    )['avg']
    
    return {
        'session_id': study_session_id,
        'total_reviews': total_reviews,
        'successful_reviews': successful_reviews,
        'failed_reviews': failed_reviews,
        'success_rate': round((successful_reviews / total_reviews) * 100, 1) if total_reviews > 0 else 0,
        'quality_distribution': quality_counts,
        'average_response_time_ms': round(avg_latency) if avg_latency else None,
        'session_start': reviews.earliest('reviewed_at').reviewed_at,
        'session_end': reviews.latest('reviewed_at').reviewed_at
    }