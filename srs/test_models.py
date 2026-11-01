"""
Comprehensive tests for SRS models.
Tests model relationships, constraints, and business logic.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta

from terminology.models import Medication, Diagnosis
from srs.models import Category, Deck, DeckItem, UserCard, ReviewLog


class CategoryModelTest(TestCase):
    """Test Category model functionality."""
    
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category",
            description="A test category for SRS",
            is_active=True
        )
    
    def test_category_creation(self):
        """Test basic category creation."""
        self.assertEqual(self.category.name, "Test Category")
        self.assertEqual(self.category.slug, "test-category")
        self.assertTrue(self.category.is_active)
        self.assertIsNotNone(self.category.created_at)
    
    def test_category_str_representation(self):
        """Test category string representation."""
        self.assertEqual(str(self.category), "Test Category")
    
    def test_category_slug_uniqueness(self):
        """Test that category slugs must be unique."""
        with self.assertRaises(IntegrityError):
            Category.objects.create(
                name="Another Category",
                slug="test-category",  # Same slug
                description="Another test category"
            )
    
    def test_category_ordering(self):
        """Test category ordering by name."""
        cat_b = Category.objects.create(name="B Category", slug="b-cat")
        cat_a = Category.objects.create(name="A Category", slug="a-cat")
        
        categories = list(Category.objects.all())
        self.assertEqual(categories[0].name, "A Category")
        self.assertEqual(categories[1].name, "B Category")
        self.assertEqual(categories[2].name, "Test Category")


class DeckModelTest(TestCase):
    """Test Deck model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name="Medical",
            slug="medical",
            description="Medical terminology"
        )
        self.deck = Deck.objects.create(
            name="Basic Medical Terms",
            description="Essential medical vocabulary",
            category=self.category,
            created_by=self.user,
            is_public=True
        )
    
    def test_deck_creation(self):
        """Test basic deck creation."""
        self.assertEqual(self.deck.name, "Basic Medical Terms")
        self.assertEqual(self.deck.category, self.category)
        self.assertEqual(self.deck.created_by, self.user)
        self.assertTrue(self.deck.is_public)
        self.assertIsNotNone(self.deck.created_at)
    
    def test_deck_str_representation(self):
        """Test deck string representation."""
        expected = "Basic Medical Terms (Medical)"
        self.assertEqual(str(self.deck), expected)
    
    def test_deck_category_relationship(self):
        """Test deck-category foreign key relationship."""
        self.assertEqual(self.deck.category.name, "Medical")
        self.assertIn(self.deck, self.category.deck_set.all())
    
    def test_deck_user_relationship(self):
        """Test deck-user foreign key relationship."""
        self.assertEqual(self.deck.created_by.username, "testuser")


class DeckItemModelTest(TestCase):
    """Test DeckItem model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name="Medical",
            slug="medical"
        )
        self.deck = Deck.objects.create(
            name="Medical Deck",
            category=self.category,
            created_by=self.user
        )
        
        # Create terminology objects
        self.medication = Medication.objects.create(
            english_term="aspirin",
            spanish_term="aspirina",
            definition="Pain reliever and anti-inflammatory drug"
        )
        self.diagnosis = Diagnosis.objects.create(
            english_term="hypertension",
            spanish_term="hipertensión",
            definition="High blood pressure condition"
        )
    
    def test_deck_item_creation_with_medication(self):
        """Test creating deck item with medication."""
        deck_item = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction=DeckItem.Direction.EN_TO_ES,
            note="Common pain medication"
        )
        
        self.assertEqual(deck_item.deck, self.deck)
        self.assertEqual(deck_item.term_content_object, self.medication)
        self.assertEqual(deck_item.direction, DeckItem.Direction.EN_TO_ES)
        self.assertEqual(deck_item.note, "Common pain medication")
    
    def test_deck_item_creation_with_diagnosis(self):
        """Test creating deck item with diagnosis."""
        deck_item = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.diagnosis,
            direction=DeckItem.Direction.ES_TO_EN
        )
        
        self.assertEqual(deck_item.term_content_object, self.diagnosis)
        self.assertEqual(deck_item.direction, DeckItem.Direction.ES_TO_EN)
    
    def test_deck_item_str_representation(self):
        """Test deck item string representation."""
        deck_item = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction=DeckItem.Direction.EN_TO_ES
        )
        
        expected = "aspirin → aspirina (Medical Deck)"
        self.assertEqual(str(deck_item), expected)
    
    def test_deck_item_unique_constraint(self):
        """Test unique constraint on deck, term, and direction."""
        # Create first deck item
        DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction=DeckItem.Direction.EN_TO_ES
        )
        
        # Try to create duplicate - should raise IntegrityError
        with self.assertRaises(IntegrityError):
            DeckItem.objects.create(
                deck=self.deck,
                term_content_object=self.medication,
                direction=DeckItem.Direction.EN_TO_ES
            )
    
    def test_deck_item_different_directions_allowed(self):
        """Test that same term with different directions is allowed."""
        # Create EN_TO_ES item
        item1 = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction=DeckItem.Direction.EN_TO_ES
        )
        
        # Create ES_TO_EN item - should be allowed
        item2 = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction=DeckItem.Direction.ES_TO_EN
        )
        
        self.assertNotEqual(item1.direction, item2.direction)
        self.assertEqual(DeckItem.objects.filter(deck=self.deck).count(), 2)


class UserCardModelTest(TestCase):
    """Test UserCard model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name="Medical",
            slug="medical"
        )
        self.deck = Deck.objects.create(
            name="Medical Deck",
            category=self.category,
            created_by=self.user
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
    
    def test_user_card_creation(self):
        """Test basic user card creation."""
        user_card = UserCard.objects.create(
            user=self.user,
            deck_item=self.deck_item
        )
        
        self.assertEqual(user_card.user, self.user)
        self.assertEqual(user_card.deck_item, self.deck_item)
        self.assertEqual(user_card.ease_factor, 2.5)  # Default SM-2 value
        self.assertEqual(user_card.interval, 0)
        self.assertEqual(user_card.repetitions, 0)
        self.assertFalse(user_card.suspended)
        self.assertEqual(user_card.lapses, 0)
    
    def test_user_card_str_representation(self):
        """Test user card string representation."""
        user_card = UserCard.objects.create(
            user=self.user,
            deck_item=self.deck_item
        )
        
        expected = "testuser: aspirin → aspirina"
        self.assertEqual(str(user_card), expected)
    
    def test_user_card_unique_constraint(self):
        """Test unique constraint on user and deck_item."""
        # Create first user card
        UserCard.objects.create(
            user=self.user,
            deck_item=self.deck_item
        )
        
        # Try to create duplicate - should raise IntegrityError
        with self.assertRaises(IntegrityError):
            UserCard.objects.create(
                user=self.user,
                deck_item=self.deck_item
            )
    
    def test_user_card_is_due_property(self):
        """Test is_due property."""
        # Card due now
        user_card = UserCard.objects.create(
            user=self.user,
            deck_item=self.deck_item,
            due=timezone.now() - timedelta(minutes=1)
        )
        self.assertTrue(user_card.is_due)
        
        # Card due in future
        user_card.due = timezone.now() + timedelta(days=1)
        user_card.save()
        self.assertFalse(user_card.is_due)
    
    def test_user_card_is_new_property(self):
        """Test is_new property."""
        user_card = UserCard.objects.create(
            user=self.user,
            deck_item=self.deck_item
        )
        
        # New card (repetitions = 0)
        self.assertTrue(user_card.is_new)
        
        # Not new card
        user_card.repetitions = 1
        user_card.save()
        self.assertFalse(user_card.is_new)
    
    def test_user_card_is_learning_property(self):
        """Test is_learning property."""
        user_card = UserCard.objects.create(
            user=self.user,
            deck_item=self.deck_item
        )
        
        # New card is not learning
        self.assertFalse(user_card.is_learning)
        
        # Learning card (repetitions > 0, interval < 21)
        user_card.repetitions = 1
        user_card.interval = 5
        user_card.save()
        self.assertTrue(user_card.is_learning)
        
        # Mature card (interval >= 21)
        user_card.interval = 25
        user_card.save()
        self.assertFalse(user_card.is_learning)
    
    def test_user_card_is_mature_property(self):
        """Test is_mature property."""
        user_card = UserCard.objects.create(
            user=self.user,
            deck_item=self.deck_item
        )
        
        # New card is not mature
        self.assertFalse(user_card.is_mature)
        
        # Learning card is not mature
        user_card.repetitions = 1
        user_card.interval = 5
        user_card.save()
        self.assertFalse(user_card.is_mature)
        
        # Mature card (interval >= 21)
        user_card.interval = 25
        user_card.save()
        self.assertTrue(user_card.is_mature)


class ReviewLogModelTest(TestCase):
    """Test ReviewLog model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name="Medical",
            slug="medical"
        )
        self.deck = Deck.objects.create(
            name="Medical Deck",
            category=self.category,
            created_by=self.user
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
    
    def test_review_log_creation(self):
        """Test basic review log creation."""
        review_log = ReviewLog.objects.create(
            user=self.user,
            deck_item=self.deck_item,
            quality=4,
            ease_factor=2.6,
            interval=3,
            repetitions=1,
            latency_ms=2500
        )
        
        self.assertEqual(review_log.user, self.user)
        self.assertEqual(review_log.deck_item, self.deck_item)
        self.assertEqual(review_log.quality, 4)
        self.assertEqual(review_log.ease_factor, 2.6)
        self.assertEqual(review_log.interval, 3)
        self.assertEqual(review_log.repetitions, 1)
        self.assertEqual(review_log.latency_ms, 2500)
        self.assertIsNotNone(review_log.reviewed_at)
    
    def test_review_log_str_representation(self):
        """Test review log string representation."""
        review_log = ReviewLog.objects.create(
            user=self.user,
            deck_item=self.deck_item,
            quality=4
        )
        
        expected = f"testuser: aspirin → aspirina (Q:4) - {review_log.reviewed_at.strftime('%Y-%m-%d')}"
        self.assertEqual(str(review_log), expected)
    
    def test_review_log_quality_validation(self):
        """Test quality field validation (0-5 range)."""
        # Valid quality values
        for quality in [0, 1, 2, 3, 4, 5]:
            review_log = ReviewLog(
                user=self.user,
                deck_item=self.deck_item,
                quality=quality
            )
            review_log.full_clean()  # Should not raise ValidationError
    
    def test_review_log_ordering(self):
        """Test review log ordering by reviewed_at descending."""
        # Create reviews with different times
        review1 = ReviewLog.objects.create(
            user=self.user,
            deck_item=self.deck_item,
            quality=3,
            reviewed_at=timezone.now() - timedelta(hours=2)
        )
        review2 = ReviewLog.objects.create(
            user=self.user,
            deck_item=self.deck_item,
            quality=4,
            reviewed_at=timezone.now() - timedelta(hours=1)
        )
        review3 = ReviewLog.objects.create(
            user=self.user,
            deck_item=self.deck_item,
            quality=5,
            reviewed_at=timezone.now()
        )
        
        reviews = list(ReviewLog.objects.all())
        self.assertEqual(reviews[0], review3)  # Most recent first
        self.assertEqual(reviews[1], review2)
        self.assertEqual(reviews[2], review1)  # Oldest last