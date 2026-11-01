"""
Comprehensive tests for the SRS (Spaced Repetition System) functionality.

This module tests the SM-2 algorithm implementation, service functions,
and model behavior to ensure accuracy and reliability.
"""

from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import IntegrityError

from terminology.models import Medication, Diagnosis
from .models import Category, Deck, DeckItem, UserCard, ReviewLog
from .algorithms import (
    sm2_update, create_initial_state, SM2State,
    get_interval_description, calculate_retention_rate,
    simulate_learning_curve, QUALITY_PERFECT, QUALITY_BLACKOUT
)
from .services import (
    get_due_usercards, ensure_usercards_exist, review_card,
    get_user_study_stats, calculate_study_streak
)


class SM2AlgorithmTests(TestCase):
    """Test the SM-2 algorithm implementation."""
    
    def setUp(self):
        self.base_time = timezone.now()
    
    def test_create_initial_state(self):
        """Test creating initial SM-2 state."""
        state = create_initial_state(self.base_time)
        
        self.assertEqual(state.ease_factor, 2.5)
        self.assertEqual(state.interval, 0)
        self.assertEqual(state.repetitions, 0)
        self.assertEqual(state.due, self.base_time)
    
    def test_sm2_update_perfect_response(self):
        """Test SM-2 update with perfect response (quality 5)."""
        initial_state = create_initial_state(self.base_time)
        result = sm2_update(initial_state, QUALITY_PERFECT, self.base_time)
        
        # First review should set interval to 1 day
        self.assertEqual(result.new_state.interval, 1)
        self.assertEqual(result.new_state.repetitions, 1)
        self.assertTrue(result.was_successful)
        self.assertTrue(result.interval_changed)
        
        # Ease factor should increase for perfect response
        self.assertGreater(result.new_state.ease_factor, initial_state.ease_factor)
    
    def test_sm2_update_failed_response(self):
        """Test SM-2 update with failed response (quality 0)."""
        # Start with a card that has some progress
        state = SM2State(
            ease_factor=2.5,
            interval=6,
            repetitions=2,
            due=self.base_time
        )
        
        result = sm2_update(state, QUALITY_BLACKOUT, self.base_time)
        
        # Failed review should reset repetitions and set short interval
        self.assertEqual(result.new_state.interval, 1)
        self.assertEqual(result.new_state.repetitions, 0)
        self.assertFalse(result.was_successful)
        
        # Ease factor should decrease significantly
        self.assertLess(result.new_state.ease_factor, state.ease_factor)
    
    def test_sm2_update_progression(self):
        """Test SM-2 progression through multiple successful reviews."""
        state = create_initial_state(self.base_time)
        
        # First review (quality 4)
        result1 = sm2_update(state, 4, self.base_time)
        self.assertEqual(result1.new_state.interval, 1)
        self.assertEqual(result1.new_state.repetitions, 1)
        
        # Second review (quality 4)
        review_time2 = self.base_time + timedelta(days=1)
        result2 = sm2_update(result1.new_state, 4, review_time2)
        self.assertEqual(result2.new_state.interval, 6)
        self.assertEqual(result2.new_state.repetitions, 2)
        
        # Third review (quality 4) - should use ease factor
        review_time3 = review_time2 + timedelta(days=6)
        result3 = sm2_update(result2.new_state, 4, review_time3)
        expected_interval = int(6 * result2.new_state.ease_factor)
        self.assertEqual(result3.new_state.interval, expected_interval)
        self.assertEqual(result3.new_state.repetitions, 3)
    
    def test_ease_factor_bounds(self):
        """Test that ease factor stays within bounds."""
        state = SM2State(
            ease_factor=1.5,
            interval=1,
            repetitions=1,
            due=self.base_time
        )
        
        # Multiple failed reviews should not push EF below 1.3
        for _ in range(10):
            result = sm2_update(state, QUALITY_BLACKOUT, self.base_time)
            state = result.new_state
            self.assertGreaterEqual(state.ease_factor, 1.3)
    
    def test_quality_validation(self):
        """Test that invalid quality values raise errors."""
        state = create_initial_state(self.base_time)
        
        with self.assertRaises(ValueError):
            sm2_update(state, -1, self.base_time)
        
        with self.assertRaises(ValueError):
            sm2_update(state, 6, self.base_time)
    
    def test_interval_description(self):
        """Test interval description formatting."""
        self.assertEqual(get_interval_description(0), "Due now")
        self.assertEqual(get_interval_description(1), "1 day")
        self.assertEqual(get_interval_description(5), "5 days")
        self.assertEqual(get_interval_description(7), "1 week")
        self.assertEqual(get_interval_description(14), "2 weeks")
        self.assertEqual(get_interval_description(30), "1 month")
        self.assertEqual(get_interval_description(365), "1 year")
    
    def test_retention_rate_calculation(self):
        """Test retention rate estimation."""
        # Test boundary values
        self.assertEqual(calculate_retention_rate(1.3), 70.0)
        self.assertGreaterEqual(calculate_retention_rate(2.5), 90.0)
        
        # Test that higher EF gives higher retention
        self.assertGreater(
            calculate_retention_rate(2.0),
            calculate_retention_rate(1.5)
        )
    
    def test_simulate_learning_curve(self):
        """Test learning curve simulation."""
        initial_state = create_initial_state(self.base_time)
        quality_sequence = [4, 4, 5, 3, 4, 5]
        
        states = simulate_learning_curve(initial_state, quality_sequence, self.base_time)
        
        # Should have initial state plus one for each quality rating
        self.assertEqual(len(states), len(quality_sequence) + 1)
        
        # Intervals should generally increase with good performance
        final_state = states[-1]
        self.assertGreater(final_state.interval, initial_state.interval)
        self.assertGreater(final_state.repetitions, initial_state.repetitions)


class SRSModelTests(TestCase):
    """Test SRS model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.deck = Deck.objects.create(
            name='Test Deck',
            category=self.category,
            created_by=self.user
        )
        
        # Create test terminology
        self.medication = Medication.objects.create(
            english_name='Aspirin',
            spanish_name='Aspirina'
        )
        
        # Create deck item
        self.deck_item = DeckItem.objects.create(
            deck=self.deck,
            content_type=ContentType.objects.get_for_model(Medication),
            object_id=self.medication.id,
            direction='EN_TO_ES'
        )
    
    def test_category_model(self):
        """Test Category model functionality."""
        self.assertEqual(str(self.category), 'Test Category')
        self.assertTrue(self.category.is_active)
        self.assertEqual(self.category.slug, 'test-category')
    
    def test_deck_model(self):
        """Test Deck model functionality."""
        self.assertEqual(str(self.deck), 'Test Category - Test Deck')
        self.assertTrue(self.deck.is_public)
        self.assertTrue(self.deck.is_active)
        self.assertEqual(self.deck.get_card_count(), 1)
    
    def test_deck_item_model(self):
        """Test DeckItem model functionality."""
        self.assertEqual(self.deck_item.get_front_text(), 'Aspirin')
        self.assertEqual(self.deck_item.get_back_text(), 'Aspirina')
        self.assertTrue(self.deck_item.is_active)
    
    def test_deck_item_unique_constraint(self):
        """Test that duplicate deck items are prevented."""
        with self.assertRaises(IntegrityError):
            DeckItem.objects.create(
                deck=self.deck,
                content_type=ContentType.objects.get_for_model(Medication),
                object_id=self.medication.id,
                direction='EN_TO_ES'  # Same as existing
            )
    
    def test_user_card_model(self):
        """Test UserCard model functionality."""
        user_card = UserCard.objects.create(
            user=self.user,
            deck_item=self.deck_item,
            ease_factor=2.5,
            interval=1,
            repetitions=0,
            due=timezone.now()
        )
        
        self.assertTrue(user_card.is_due())
        self.assertEqual(user_card.days_until_due(), 0)
        
        # Test future due date
        future_due = timezone.now() + timedelta(days=5)
        user_card.due = future_due
        user_card.save()
        self.assertFalse(user_card.is_due())
        # days_until_due() can be 4 or 5 depending on timing, so check it's >= 4
        self.assertGreaterEqual(user_card.days_until_due(), 4)
    
    def test_review_log_model(self):
        """Test ReviewLog model functionality."""
        user_card = UserCard.objects.create(
            user=self.user,
            deck_item=self.deck_item
        )
        
        review_log = ReviewLog.objects.create(
            user=self.user,
            deck_item=self.deck_item,
            quality=4,
            ease_factor=2.5,
            interval=6,
            repetitions=2
        )
        
        self.assertTrue(review_log.was_successful())
        self.assertEqual(review_log.get_quality_display_text(), 
                        "Correct response after hesitation")


class SRSServiceTests(TestCase):
    """Test SRS service functions."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.deck = Deck.objects.create(
            name='Test Deck',
            category=self.category,
            created_by=self.user
        )
        
        # Create multiple test medications
        self.medications = []
        for i in range(5):
            med = Medication.objects.create(
                english_name=f'Medicine {i}',
                spanish_name=f'Medicina {i}'
            )
            self.medications.append(med)
            
            DeckItem.objects.create(
                deck=self.deck,
                content_type=ContentType.objects.get_for_model(Medication),
                object_id=med.id,
                direction='EN_TO_ES'
            )
    
    def test_ensure_usercards_exist(self):
        """Test creating user cards for deck items."""
        # Initially no user cards exist
        self.assertEqual(UserCard.objects.filter(user=self.user).count(), 0)
        
        # Create user cards
        created_count = ensure_usercards_exist(self.user, self.deck)
        
        self.assertEqual(created_count, 5)  # 5 medications
        self.assertEqual(UserCard.objects.filter(user=self.user).count(), 5)
        
        # Running again should create no new cards
        created_count = ensure_usercards_exist(self.user, self.deck)
        self.assertEqual(created_count, 0)
    
    def test_get_due_usercards(self):
        """Test retrieving due cards for a user."""
        ensure_usercards_exist(self.user, self.deck)
        
        # All new cards should be due
        due_cards = get_due_usercards(self.user)
        self.assertEqual(len(due_cards), 5)
        
        # Set some cards to future dates
        user_cards = UserCard.objects.filter(user=self.user)[:2]
        for card in user_cards:
            card.due = timezone.now() + timedelta(days=5)
            card.last_reviewed = timezone.now()  # Mark as reviewed so they're not "new"
            card.save()
        
        # Should now return fewer due cards (only the ones still due)
        due_cards = get_due_usercards(self.user)
        self.assertEqual(len(due_cards), 3)
    
    def test_review_card(self):
        """Test reviewing a card."""
        ensure_usercards_exist(self.user, self.deck)
        deck_item = DeckItem.objects.filter(deck=self.deck).first()
        
        # Review with good quality
        result = review_card(self.user, deck_item.id, 4)
        
        self.assertTrue(result['success'])
        self.assertTrue(result['was_successful'])
        self.assertIsNotNone(result['user_card'])
        self.assertIsNotNone(result['review_log'])
        
        # Check that user card was updated
        user_card = UserCard.objects.get(user=self.user, deck_item=deck_item)
        self.assertIsNotNone(user_card.last_reviewed)
        self.assertEqual(user_card.repetitions, 1)
        
        # Check that review log was created
        self.assertTrue(ReviewLog.objects.filter(
            user=self.user,
            deck_item=deck_item,
            quality=4
        ).exists())
    
    def test_get_user_study_stats(self):
        """Test getting user study statistics."""
        ensure_usercards_exist(self.user, self.deck)
        
        # Review some cards
        deck_items = DeckItem.objects.filter(deck=self.deck)[:3]
        for deck_item in deck_items:
            review_card(self.user, deck_item.id, 4)
        
        stats = get_user_study_stats(self.user)
        
        self.assertEqual(stats['total_cards'], 5)
        self.assertEqual(stats['total_reviews'], 3)
        self.assertGreater(stats['success_rate'], 0)
        self.assertEqual(stats['recent_reviews'], 3)
    
    def test_calculate_study_streak(self):
        """Test calculating study streak."""
        ensure_usercards_exist(self.user, self.deck)
        deck_item = DeckItem.objects.filter(deck=self.deck).first()
        
        # No reviews yet
        streak = calculate_study_streak(self.user)
        self.assertEqual(streak, 0)
        
        # Review today
        review_card(self.user, deck_item.id, 4)
        streak = calculate_study_streak(self.user)
        self.assertEqual(streak, 1)
        
        # Create a review for yesterday
        yesterday = timezone.now() - timedelta(days=1)
        ReviewLog.objects.create(
            user=self.user,
            deck_item=deck_item,
            quality=4,
            ease_factor=2.5,
            interval=1,
            repetitions=1,
            reviewed_at=yesterday
        )
        
        streak = calculate_study_streak(self.user)
        self.assertEqual(streak, 2)


class SRSIntegrationTests(TestCase):
    """Integration tests for the complete SRS workflow."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create categories and decks
        self.medical_category = Category.objects.create(
            name='Medical',
            slug='medical',
            icon_class='fas fa-stethoscope',
            color_class='primary'
        )
        
        self.medical_deck = Deck.objects.create(
            name='Basic Medications',
            category=self.medical_category,
            created_by=self.user
        )
        
        # Create test data
        medications = [
            ('Aspirin', 'Aspirina'),
            ('Ibuprofen', 'Ibuprofeno'),
            ('Acetaminophen', 'Acetaminofén')
        ]
        
        for eng, esp in medications:
            med = Medication.objects.create(
                english_name=eng,
                spanish_name=esp
            )
            DeckItem.objects.create(
                deck=self.medical_deck,
                content_type=ContentType.objects.get_for_model(Medication),
                object_id=med.id,
                direction='EN_TO_ES'
            )
    
    def test_complete_study_workflow(self):
        """Test a complete study workflow from start to finish."""
        # 1. Initialize user cards
        created_count = ensure_usercards_exist(self.user, self.medical_deck)
        self.assertEqual(created_count, 3)
        
        # 2. Get due cards for study
        due_cards = get_due_usercards(self.user, self.medical_category.id)
        self.assertEqual(len(due_cards), 3)
        
        # 3. Study session - review all cards
        session_id = 'test-session-123'
        review_results = []
        
        for user_card in due_cards:
            result = review_card(
                self.user,
                user_card.deck_item.id,
                4,  # Good quality
                study_session_id=session_id
            )
            review_results.append(result)
            self.assertTrue(result['success'])
        
        # 4. Check that cards are no longer due
        due_cards_after = get_due_usercards(self.user, self.medical_category.id)
        self.assertEqual(len(due_cards_after), 0)
        
        # 5. Verify statistics
        stats = get_user_study_stats(self.user, self.medical_category.id)
        self.assertEqual(stats['total_reviews'], 3)
        self.assertEqual(stats['success_rate'], 100.0)
        self.assertEqual(stats['recent_reviews'], 3)
        
        # 6. Check study streak
        streak = calculate_study_streak(self.user)
        self.assertEqual(streak, 1)
    
    def test_mixed_quality_reviews(self):
        """Test reviewing cards with different quality ratings."""
        ensure_usercards_exist(self.user, self.medical_deck)
        deck_items = list(DeckItem.objects.filter(deck=self.medical_deck))
        
        # Review with different qualities
        qualities = [5, 3, 1]  # Perfect, Hard, Failed
        
        for i, deck_item in enumerate(deck_items):
            review_card(self.user, deck_item.id, qualities[i])
        
        # Check results
        user_cards = UserCard.objects.filter(user=self.user).order_by('id')
        
        # Perfect response should have higher ease factor
        perfect_card = user_cards[0]
        self.assertGreater(perfect_card.ease_factor, 2.5)
        self.assertEqual(perfect_card.repetitions, 1)
        
        # Hard response should have lower ease factor but still successful
        hard_card = user_cards[1]
        self.assertLess(hard_card.ease_factor, 2.5)
        self.assertEqual(hard_card.repetitions, 1)
        
        # Failed response should reset repetitions
        failed_card = user_cards[2]
        self.assertEqual(failed_card.repetitions, 0)
        self.assertEqual(failed_card.lapses, 1)
        
        # Check overall statistics
        stats = get_user_study_stats(self.user)
        self.assertAlmostEqual(stats['success_rate'], 66.7, places=1)  # 2/3 successful
