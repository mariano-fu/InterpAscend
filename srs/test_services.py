"""
Comprehensive tests for SRS services and algorithms.
Tests SM-2 algorithm accuracy, service functions, and business logic.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime
from unittest.mock import patch

from terminology.models import Medication, Diagnosis
from srs.models import Category, Deck, DeckItem, UserCard, ReviewLog
from srs.algorithms import SM2State, SM2Result, sm2_update, next_due
from srs.services import (
    get_due_usercards, ensure_usercards_exist, review_card,
    get_user_study_stats, get_category_progress
)


class SM2AlgorithmTest(TestCase):
    """Test SM-2 algorithm implementation."""
    
    def test_sm2_state_creation(self):
        """Test SM2State dataclass creation."""
        state = SM2State(
            ease_factor=2.5,
            interval=1,
            repetitions=0
        )
        
        self.assertEqual(state.ease_factor, 2.5)
        self.assertEqual(state.interval, 1)
        self.assertEqual(state.repetitions, 0)
    
    def test_sm2_result_creation(self):
        """Test SM2Result dataclass creation."""
        result = SM2Result(
            ease_factor=2.6,
            interval=3,
            repetitions=1,
            due_date=timezone.now() + timedelta(days=3)
        )
        
        self.assertEqual(result.ease_factor, 2.6)
        self.assertEqual(result.interval, 3)
        self.assertEqual(result.repetitions, 1)
        self.assertIsInstance(result.due_date, datetime)
    
    def test_sm2_algorithm_quality_0_again(self):
        """Test SM-2 algorithm with quality 0 (Again)."""
        state = SM2State(ease_factor=2.5, interval=1, repetitions=1)
        result = sm2_update(state, quality=0)
        
        # Quality 0 should reset repetitions and set interval to 1
        self.assertEqual(result.repetitions, 0)
        self.assertEqual(result.interval, 1)
        self.assertLess(result.ease_factor, 2.5)  # EF should decrease
        self.assertGreaterEqual(result.ease_factor, 1.3)  # EF floor
    
    def test_sm2_algorithm_quality_1_again(self):
        """Test SM-2 algorithm with quality 1 (Again)."""
        state = SM2State(ease_factor=2.5, interval=5, repetitions=2)
        result = sm2_update(state, quality=1)
        
        # Quality 1 should reset repetitions and set interval to 1
        self.assertEqual(result.repetitions, 0)
        self.assertEqual(result.interval, 1)
        self.assertLess(result.ease_factor, 2.5)
    
    def test_sm2_algorithm_quality_2_hard(self):
        """Test SM-2 algorithm with quality 2 (Hard)."""
        state = SM2State(ease_factor=2.5, interval=5, repetitions=2)
        result = sm2_update(state, quality=2)
        
        # Quality 2 should reset repetitions but keep some interval
        self.assertEqual(result.repetitions, 0)
        self.assertGreater(result.interval, 1)
        self.assertLess(result.ease_factor, 2.5)
    
    def test_sm2_algorithm_quality_3_hard(self):
        """Test SM-2 algorithm with quality 3 (Hard)."""
        state = SM2State(ease_factor=2.5, interval=5, repetitions=2)
        result = sm2_update(state, quality=3)
        
        # Quality 3 should reset repetitions
        self.assertEqual(result.repetitions, 0)
        self.assertLess(result.ease_factor, 2.5)
    
    def test_sm2_algorithm_quality_4_good(self):
        """Test SM-2 algorithm with quality 4 (Good)."""
        state = SM2State(ease_factor=2.5, interval=1, repetitions=0)
        result = sm2_update(state, quality=4)
        
        # First repetition with quality 4
        self.assertEqual(result.repetitions, 1)
        self.assertEqual(result.interval, 1)
        self.assertGreaterEqual(result.ease_factor, 2.5)
        
        # Second repetition
        state = SM2State(ease_factor=result.ease_factor, interval=result.interval, repetitions=result.repetitions)
        result = sm2_update(state, quality=4)
        
        self.assertEqual(result.repetitions, 2)
        self.assertEqual(result.interval, 6)
        
        # Third repetition
        state = SM2State(ease_factor=result.ease_factor, interval=result.interval, repetitions=result.repetitions)
        result = sm2_update(state, quality=4)
        
        self.assertEqual(result.repetitions, 3)
        self.assertGreater(result.interval, 6)
    
    def test_sm2_algorithm_quality_5_easy(self):
        """Test SM-2 algorithm with quality 5 (Easy)."""
        state = SM2State(ease_factor=2.5, interval=1, repetitions=0)
        result = sm2_update(state, quality=5)
        
        # Quality 5 should increase ease factor more than quality 4
        self.assertEqual(result.repetitions, 1)
        self.assertGreater(result.ease_factor, 2.5)
    
    def test_sm2_ease_factor_floor(self):
        """Test that ease factor never goes below 1.3."""
        state = SM2State(ease_factor=1.4, interval=1, repetitions=1)
        result = sm2_update(state, quality=0)
        
        self.assertGreaterEqual(result.ease_factor, 1.3)
    
    def test_next_due_function(self):
        """Test next_due helper function."""
        now = timezone.now()
        
        # Test with 0 days
        due_date = next_due(now, 0)
        self.assertEqual(due_date.date(), now.date())
        
        # Test with positive days
        due_date = next_due(now, 5)
        expected_date = (now + timedelta(days=5)).date()
        self.assertEqual(due_date.date(), expected_date)


class SRSServicesTest(TestCase):
    """Test SRS service functions."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        self.category = Category.objects.create(
            name="Medical",
            slug="medical",
            is_active=True
        )
        
        self.deck = Deck.objects.create(
            name="Medical Terms",
            category=self.category,
            created_by=self.user,
            is_public=True
        )
        
        # Create terminology objects
        self.medication1 = Medication.objects.create(
            english_term="aspirin",
            spanish_term="aspirina",
            definition="Pain reliever"
        )
        self.medication2 = Medication.objects.create(
            english_term="ibuprofen",
            spanish_term="ibuprofeno",
            definition="Anti-inflammatory"
        )
        
        # Create deck items
        self.deck_item1 = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication1,
            direction=DeckItem.Direction.EN_TO_ES
        )
        self.deck_item2 = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication2,
            direction=DeckItem.Direction.EN_TO_ES
        )
    
    def test_ensure_usercards_exist(self):
        """Test ensure_usercards_exist service function."""
        # Initially no user cards exist
        self.assertEqual(UserCard.objects.filter(user=self.user).count(), 0)
        
        # Call service function
        ensure_usercards_exist(self.user, self.deck)
        
        # Should create user cards for all deck items
        user_cards = UserCard.objects.filter(user=self.user)
        self.assertEqual(user_cards.count(), 2)
        
        # Check that cards are properly initialized
        for card in user_cards:
            self.assertEqual(card.ease_factor, 2.5)
            self.assertEqual(card.interval, 0)
            self.assertEqual(card.repetitions, 0)
            self.assertFalse(card.suspended)
    
    def test_ensure_usercards_exist_idempotent(self):
        """Test that ensure_usercards_exist is idempotent."""
        # Call twice
        ensure_usercards_exist(self.user, self.deck)
        ensure_usercards_exist(self.user, self.deck)
        
        # Should still only have 2 cards
        self.assertEqual(UserCard.objects.filter(user=self.user).count(), 2)
    
    def test_get_due_usercards_empty(self):
        """Test get_due_usercards with no cards."""
        due_cards = get_due_usercards(self.user)
        self.assertEqual(len(due_cards), 0)
    
    def test_get_due_usercards_with_due_cards(self):
        """Test get_due_usercards with due cards."""
        # Create user cards
        ensure_usercards_exist(self.user, self.deck)
        
        # All new cards should be due
        due_cards = get_due_usercards(self.user)
        self.assertEqual(len(due_cards), 2)
    
    def test_get_due_usercards_with_future_cards(self):
        """Test get_due_usercards excludes future cards."""
        # Create user cards
        ensure_usercards_exist(self.user, self.deck)
        
        # Set one card to be due in the future
        user_card = UserCard.objects.filter(user=self.user).first()
        user_card.due = timezone.now() + timedelta(days=1)
        user_card.save()
        
        # Should only return 1 due card
        due_cards = get_due_usercards(self.user)
        self.assertEqual(len(due_cards), 1)
    
    def test_get_due_usercards_category_filter(self):
        """Test get_due_usercards with category filter."""
        # Create another category and deck
        other_category = Category.objects.create(
            name="Financial",
            slug="financial",
            is_active=True
        )
        other_deck = Deck.objects.create(
            name="Financial Terms",
            category=other_category,
            created_by=self.user
        )
        
        # Create user cards for both decks
        ensure_usercards_exist(self.user, self.deck)
        ensure_usercards_exist(self.user, other_deck)
        
        # Filter by medical category
        due_cards = get_due_usercards(self.user, category_id=self.category.id)
        self.assertEqual(len(due_cards), 2)
        
        # Filter by financial category (no cards)
        due_cards = get_due_usercards(self.user, category_id=other_category.id)
        self.assertEqual(len(due_cards), 0)
    
    def test_get_due_usercards_limit(self):
        """Test get_due_usercards with limit."""
        # Create user cards
        ensure_usercards_exist(self.user, self.deck)
        
        # Test limit
        due_cards = get_due_usercards(self.user, limit=1)
        self.assertEqual(len(due_cards), 1)
    
    def test_get_due_usercards_user_isolation(self):
        """Test that get_due_usercards isolates users."""
        # Create cards for both users
        ensure_usercards_exist(self.user, self.deck)
        ensure_usercards_exist(self.other_user, self.deck)
        
        # Each user should only see their own cards
        user_cards = get_due_usercards(self.user)
        other_user_cards = get_due_usercards(self.other_user)
        
        self.assertEqual(len(user_cards), 2)
        self.assertEqual(len(other_user_cards), 2)
        
        # Verify user isolation
        for card in user_cards:
            self.assertEqual(card.user, self.user)
        for card in other_user_cards:
            self.assertEqual(card.user, self.other_user)
    
    def test_review_card_service(self):
        """Test review_card service function."""
        # Create user card
        ensure_usercards_exist(self.user, self.deck)
        user_card = UserCard.objects.filter(user=self.user).first()
        
        # Review with quality 4
        result = review_card(self.user, user_card.deck_item.id, quality=4)
        
        # Check result
        self.assertIsNotNone(result)
        self.assertEqual(result['quality'], 4)
        self.assertIn('next_due', result)
        
        # Check user card was updated
        user_card.refresh_from_db()
        self.assertEqual(user_card.repetitions, 1)
        self.assertGreater(user_card.ease_factor, 0)
        
        # Check review log was created
        review_log = ReviewLog.objects.filter(
            user=self.user,
            deck_item=user_card.deck_item
        ).first()
        self.assertIsNotNone(review_log)
        self.assertEqual(review_log.quality, 4)
    
    def test_review_card_with_latency(self):
        """Test review_card with response latency."""
        ensure_usercards_exist(self.user, self.deck)
        user_card = UserCard.objects.filter(user=self.user).first()
        
        # Review with latency
        result = review_card(
            self.user, 
            user_card.deck_item.id, 
            quality=4, 
            latency_ms=2500
        )
        
        # Check review log includes latency
        review_log = ReviewLog.objects.filter(
            user=self.user,
            deck_item=user_card.deck_item
        ).first()
        self.assertEqual(review_log.latency_ms, 2500)
    
    def test_review_card_nonexistent(self):
        """Test review_card with nonexistent deck item."""
        result = review_card(self.user, 99999, quality=4)
        self.assertIsNone(result)
    
    def test_get_user_study_stats(self):
        """Test get_user_study_stats service function."""
        # Create user cards and reviews
        ensure_usercards_exist(self.user, self.deck)
        user_card = UserCard.objects.filter(user=self.user).first()
        
        # Create some review history
        ReviewLog.objects.create(
            user=self.user,
            deck_item=user_card.deck_item,
            quality=4,
            ease_factor=2.6,
            interval=3,
            repetitions=1
        )
        
        stats = get_user_study_stats(self.user)
        
        # Check stats structure
        self.assertIn('total_cards', stats)
        self.assertIn('due_cards', stats)
        self.assertIn('new_cards', stats)
        self.assertIn('young_cards', stats)
        self.assertIn('mature_cards', stats)
        self.assertIn('success_rate', stats)
        self.assertIn('average_ease_factor', stats)
        self.assertIn('study_streak', stats)
        self.assertIn('retention_estimate', stats)
        
        # Check values
        self.assertEqual(stats['total_cards'], 2)
        self.assertGreaterEqual(stats['due_cards'], 0)
        self.assertGreaterEqual(stats['success_rate'], 0)
        self.assertLessEqual(stats['success_rate'], 100)
    
    def test_get_category_progress(self):
        """Test get_category_progress service function."""
        # Create user cards
        ensure_usercards_exist(self.user, self.deck)
        
        progress = get_category_progress(self.user)
        
        # Should have one category
        self.assertEqual(len(progress), 1)
        
        category_data = progress[0]
        self.assertEqual(category_data['category'], self.category)
        self.assertEqual(category_data['total_cards'], 2)
        self.assertIn('due_cards', category_data)
        self.assertIn('success_rate', category_data)
        self.assertIn('recent_reviews', category_data)
    
    def test_get_category_progress_empty(self):
        """Test get_category_progress with no user cards."""
        progress = get_category_progress(self.user)
        self.assertEqual(len(progress), 0)
    
    def test_suspended_cards_excluded(self):
        """Test that suspended cards are excluded from due cards."""
        # Create user cards
        ensure_usercards_exist(self.user, self.deck)
        
        # Suspend one card
        user_card = UserCard.objects.filter(user=self.user).first()
        user_card.suspended = True
        user_card.save()
        
        # Should only return 1 due card
        due_cards = get_due_usercards(self.user)
        self.assertEqual(len(due_cards), 1)
        
        # Verify the suspended card is not included
        for card in due_cards:
            self.assertFalse(card.suspended)


class SRSIntegrationTest(TestCase):
    """Integration tests for the complete SRS workflow."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name="Medical",
            slug="medical",
            is_active=True
        )
        
        self.deck = Deck.objects.create(
            name="Medical Terms",
            category=self.category,
            created_by=self.user,
            is_public=True
        )
        
        self.medication = Medication.objects.create(
            english_term="aspirin",
            spanish_term="aspirina",
            definition="Pain reliever"
        )
        
        self.deck_item = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction=DeckItem.Direction.EN_TO_ES
        )
    
    def test_complete_study_workflow(self):
        """Test complete study workflow from start to finish."""
        # 1. Initialize user cards
        ensure_usercards_exist(self.user, self.deck)
        
        # 2. Get due cards
        due_cards = get_due_usercards(self.user)
        self.assertEqual(len(due_cards), 1)
        
        user_card = due_cards[0]
        self.assertTrue(user_card.is_new)
        self.assertTrue(user_card.is_due)
        
        # 3. Review card with good quality
        result = review_card(self.user, user_card.deck_item.id, quality=4)
        self.assertIsNotNone(result)
        
        # 4. Check card state after review
        user_card.refresh_from_db()
        self.assertEqual(user_card.repetitions, 1)
        self.assertFalse(user_card.is_new)
        
        # 5. Review again
        result = review_card(self.user, user_card.deck_item.id, quality=4)
        user_card.refresh_from_db()
        self.assertEqual(user_card.repetitions, 2)
        self.assertEqual(user_card.interval, 6)
        
        # 6. Check review logs
        review_logs = ReviewLog.objects.filter(
            user=self.user,
            deck_item=user_card.deck_item
        ).order_by('-reviewed_at')
        self.assertEqual(review_logs.count(), 2)
        
        # 7. Get stats
        stats = get_user_study_stats(self.user)
        self.assertEqual(stats['total_cards'], 1)
        self.assertGreater(stats['success_rate'], 0)
    
    def test_failing_card_workflow(self):
        """Test workflow with failing card (quality 0-1)."""
        # Initialize and get card
        ensure_usercards_exist(self.user, self.deck)
        user_card = UserCard.objects.filter(user=self.user).first()
        
        # Review with poor quality
        result = review_card(self.user, user_card.deck_item.id, quality=0)
        
        # Card should reset
        user_card.refresh_from_db()
        self.assertEqual(user_card.repetitions, 0)
        self.assertEqual(user_card.interval, 1)
        self.assertLess(user_card.ease_factor, 2.5)
        
        # Should still be due
        due_cards = get_due_usercards(self.user)
        self.assertEqual(len(due_cards), 1)