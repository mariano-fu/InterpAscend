"""
Comprehensive tests for SRS views and user interactions.
Tests authentication, HTMX endpoints, and user workflows.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json

from terminology.models import Medication, Diagnosis
from srs.models import Category, Deck, DeckItem, UserCard, ReviewLog
from srs.services import ensure_usercards_exist


class SRSViewsAuthenticationTest(TestCase):
    """Test authentication requirements for SRS views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication."""
        response = self.client.get(reverse('srs:dashboard'))
        self.assertRedirects(response, '/srs/login/?next=/srs/')
    
    def test_category_list_requires_login(self):
        """Test that category list requires authentication."""
        response = self.client.get(reverse('srs:category_list'))
        self.assertRedirects(response, '/srs/login/?next=/srs/categories/')
    
    def test_user_stats_requires_login(self):
        """Test that user stats requires authentication."""
        response = self.client.get(reverse('srs:user_stats'))
        self.assertRedirects(response, '/srs/login/?next=/srs/stats/')
    
    def test_study_session_requires_login(self):
        """Test that study session requires authentication."""
        response = self.client.get(reverse('srs:study_session', kwargs={'category_slug': 'medical'}))
        self.assertRedirects(response, '/srs/login/?next=/srs/study/medical/')
    
    def test_authenticated_access_works(self):
        """Test that authenticated users can access views."""
        self.client.login(username='testuser', password='testpass123')
        
        # Dashboard should work
        response = self.client.get(reverse('srs:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Category list should work
        response = self.client.get(reverse('srs:category_list'))
        self.assertEqual(response.status_code, 200)
        
        # User stats should work
        response = self.client.get(reverse('srs:user_stats'))
        self.assertEqual(response.status_code, 200)


class SRSDashboardViewTest(TestCase):
    """Test SRS dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.category = Category.objects.create(
            name="Medical",
            slug="medical",
            is_active=True
        )
        self.deck = Deck.objects.create(
            name="Medical Terms",
            category=self.category,
            created_by=self.user
        )
    
    def test_dashboard_renders_correctly(self):
        """Test dashboard renders with correct context."""
        response = self.client.get(reverse('srs:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        self.assertContains(response, 'testuser')
        self.assertIn('categories', response.context)
        self.assertIn('overall_stats', response.context)
    
    def test_dashboard_shows_categories(self):
        """Test dashboard shows active categories."""
        response = self.client.get(reverse('srs:dashboard'))
        
        self.assertContains(response, 'Medical')
        self.assertEqual(len(response.context['categories']), 1)
    
    def test_dashboard_hides_inactive_categories(self):
        """Test dashboard hides inactive categories."""
        # Create inactive category
        Category.objects.create(
            name="Inactive Category",
            slug="inactive",
            is_active=False
        )
        
        response = self.client.get(reverse('srs:dashboard'))
        
        self.assertNotContains(response, 'Inactive Category')
        self.assertEqual(len(response.context['categories']), 1)


class SRSCategoryListViewTest(TestCase):
    """Test SRS category list view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.category1 = Category.objects.create(
            name="Medical",
            slug="medical",
            is_active=True
        )
        self.category2 = Category.objects.create(
            name="Financial",
            slug="financial",
            is_active=True
        )
    
    def test_category_list_renders_correctly(self):
        """Test category list renders with correct context."""
        response = self.client.get(reverse('srs:category_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Study Categories')
        self.assertIn('categories', response.context)
    
    def test_category_list_shows_all_active_categories(self):
        """Test category list shows all active categories."""
        response = self.client.get(reverse('srs:category_list'))
        
        self.assertContains(response, 'Medical')
        self.assertContains(response, 'Financial')
        self.assertEqual(len(response.context['categories']), 2)


class SRSStudySessionViewTest(TestCase):
    """Test SRS study session view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.category = Category.objects.create(
            name="Medical",
            slug="medical",
            is_active=True
        )
        self.deck = Deck.objects.create(
            name="Medical Terms",
            category=self.category,
            created_by=self.user
        )
        
        self.medication = Medication.objects.create(
            english_name="aspirin",
            spanish_name="aspirina"
        )
        self.deck_item = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction='EN_TO_ES'
        )
    
    def test_study_session_renders_correctly(self):
        """Test study session renders with correct context."""
        response = self.client.get(reverse('srs:study_session', kwargs={'category_slug': 'medical'}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Study Session')
        self.assertIn('category', response.context)
        self.assertEqual(response.context['category'], self.category)
    
    def test_study_session_invalid_category(self):
        """Test study session with invalid category returns 404."""
        response = self.client.get(reverse('srs:study_session', kwargs={'category_slug': 'nonexistent'}))
        self.assertEqual(response.status_code, 404)
    
    def test_study_session_inactive_category(self):
        """Test study session with inactive category returns 404."""
        inactive_category = Category.objects.create(
            name="Inactive",
            slug="inactive",
            is_active=False
        )
        
        response = self.client.get(reverse('srs:study_session', kwargs={'category_slug': 'inactive'}))
        self.assertEqual(response.status_code, 404)


class SRSHTMXEndpointsTest(TestCase):
    """Test HTMX endpoints for study sessions."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.category = Category.objects.create(
            name="Medical",
            slug="medical",
            is_active=True
        )
        self.deck = Deck.objects.create(
            name="Medical Terms",
            category=self.category,
            created_by=self.user
        )
        
        self.medication = Medication.objects.create(
            english_name="aspirin",
            spanish_name="aspirina"
        )
        self.deck_item = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction='EN_TO_ES'
        )
        
        # Initialize user cards
        ensure_usercards_exist(self.user, self.deck)
    
    def test_get_next_card_endpoint(self):
        """Test get_next_card HTMX endpoint."""
        response = self.client.get(
            reverse('srs:get_next_card', kwargs={'category_slug': 'medical'}),
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aspirin')
    
    def test_get_next_card_no_cards(self):
        """Test get_next_card when no cards are due."""
        # Set card to be due in future
        user_card = UserCard.objects.filter(user=self.user).first()
        user_card.due = timezone.now() + timedelta(days=1)
        user_card.save()
        
        response = self.client.get(
            reverse('srs:get_next_card', kwargs={'category_slug': 'medical'}),
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All caught up')
    
    def test_show_answer_endpoint(self):
        """Test show_answer HTMX endpoint."""
        user_card = UserCard.objects.filter(user=self.user).first()
        
        response = self.client.post(
            reverse('srs:show_answer', kwargs={'category_slug': 'medical'}),
            {'deck_item_id': user_card.deck_item.id},
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aspirina')
        self.assertContains(response, 'Again')
        self.assertContains(response, 'Good')
    
    def test_show_answer_invalid_card(self):
        """Test show_answer with invalid card ID."""
        response = self.client.post(
            reverse('srs:show_answer', kwargs={'category_slug': 'medical'}),
            {'deck_item_id': 99999},
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_review_card_endpoint(self):
        """Test review_card HTMX endpoint."""
        user_card = UserCard.objects.filter(user=self.user).first()
        
        response = self.client.post(
            reverse('srs:review_card', kwargs={'category_slug': 'medical'}),
            {
                'card_id': user_card.id,
                'quality': 4,
                'response_time': 2500
            },
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that card was updated
        user_card.refresh_from_db()
        self.assertEqual(user_card.repetitions, 1)
        
        # Check that review log was created
        review_log = ReviewLog.objects.filter(
            user=self.user,
            deck_item=user_card.deck_item
        ).first()
        self.assertIsNotNone(review_log)
        self.assertEqual(review_log.quality, 4)
        self.assertEqual(review_log.latency_ms, 2500)
    
    def test_review_card_json_response(self):
        """Test review_card returns JSON for AJAX requests."""
        user_card = UserCard.objects.filter(user=self.user).first()
        
        response = self.client.post(
            reverse('srs:review_card', kwargs={'category_slug': 'medical'}),
            json.dumps({
                'card_id': user_card.id,
                'quality': 4,
                'response_time': 2500
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('next_due', data)
    
    def test_review_card_invalid_quality(self):
        """Test review_card with invalid quality value."""
        user_card = UserCard.objects.filter(user=self.user).first()
        
        response = self.client.post(
            reverse('srs:review_card', kwargs={'category_slug': 'medical'}),
            {
                'card_id': user_card.id,
                'quality': 10  # Invalid quality
            },
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 400)


class SRSUserStatsViewTest(TestCase):
    """Test SRS user statistics view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.category = Category.objects.create(
            name="Medical",
            slug="medical",
            is_active=True
        )
        self.deck = Deck.objects.create(
            name="Medical Terms",
            category=self.category,
            created_by=self.user
        )
        
        self.medication = Medication.objects.create(
            english_name="aspirin",
            spanish_name="aspirina"
        )
        self.deck_item = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction='EN_TO_ES'
        )
    
    def test_user_stats_renders_correctly(self):
        """Test user stats renders with correct context."""
        response = self.client.get(reverse('srs:user_stats'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your Progress')
        self.assertIn('overall_stats', response.context)
        self.assertIn('category_progress', response.context)
        self.assertIn('recent_reviews', response.context)
        self.assertIn('chart_data_json', response.context)
    
    def test_user_stats_with_data(self):
        """Test user stats with actual study data."""
        # Create user cards and review history
        ensure_usercards_exist(self.user, self.deck)
        user_card = UserCard.objects.filter(user=self.user).first()
        
        ReviewLog.objects.create(
            user=self.user,
            deck_item=user_card.deck_item,
            quality=4,
            ease_factor=2.6,
            interval=3,
            repetitions=1
        )
        
        response = self.client.get(reverse('srs:user_stats'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Medical')
        
        # Check that stats are calculated
        stats = response.context['overall_stats']
        self.assertGreater(stats['total_cards'], 0)


class SRSSignUpViewTest(TestCase):
    """Test SRS signup view."""
    
    def setUp(self):
        self.client = Client()
    
    def test_signup_get(self):
        """Test signup form renders correctly."""
        response = self.client.get(reverse('srs:signup'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')
        self.assertContains(response, 'Username')
        self.assertContains(response, 'Password')
    
    def test_signup_post_valid(self):
        """Test successful user registration."""
        response = self.client.post(reverse('srs:signup'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        })
        
        # Should redirect to dashboard after successful signup
        self.assertRedirects(response, reverse('srs:dashboard'))
        
        # User should be created and logged in
        user = User.objects.get(username='newuser')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'new@example.com')
    
    def test_signup_post_invalid(self):
        """Test signup with invalid data."""
        response = self.client.post(reverse('srs:signup'), {
            'username': 'newuser',
            'email': 'invalid-email',
            'password1': 'pass',
            'password2': 'different'
        })
        
        # Should stay on signup page with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')


class SRSUserIsolationTest(TestCase):
    """Test that users can only see their own data."""
    
    def setUp(self):
        self.client = Client()
        
        # Create two users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        # Create shared category and deck
        self.category = Category.objects.create(
            name="Medical",
            slug="medical",
            is_active=True
        )
        self.deck = Deck.objects.create(
            name="Medical Terms",
            category=self.category,
            created_by=self.user1,
            is_public=True
        )
        
        self.medication = Medication.objects.create(
            english_name="aspirin",
            spanish_name="aspirina"
        )
        self.deck_item = DeckItem.objects.create(
            deck=self.deck,
            term_content_object=self.medication,
            direction='EN_TO_ES'
        )
        
        # Create user cards for both users
        ensure_usercards_exist(self.user1, self.deck)
        ensure_usercards_exist(self.user2, self.deck)
        
        # Create review history for user1
        user1_card = UserCard.objects.filter(user=self.user1).first()
        ReviewLog.objects.create(
            user=self.user1,
            deck_item=user1_card.deck_item,
            quality=4
        )
    
    def test_user_stats_isolation(self):
        """Test that user stats only show user's own data."""
        # Login as user1
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('srs:user_stats'))
        
        # Should see own review history
        self.assertEqual(len(response.context['recent_reviews']), 1)
        
        # Login as user2
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(reverse('srs:user_stats'))
        
        # Should not see user1's review history
        self.assertEqual(len(response.context['recent_reviews']), 0)
    
    def test_study_session_isolation(self):
        """Test that study sessions only show user's own cards."""
        # Login as user1 and get next card
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(
            reverse('srs:get_next_card', kwargs={'category_slug': 'medical'}),
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Login as user2 and get next card
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(
            reverse('srs:get_next_card', kwargs={'category_slug': 'medical'}),
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Both users should have independent progress
        user1_cards = UserCard.objects.filter(user=self.user1)
        user2_cards = UserCard.objects.filter(user=self.user2)
        
        self.assertEqual(user1_cards.count(), 1)
        self.assertEqual(user2_cards.count(), 1)
        self.assertNotEqual(user1_cards.first().id, user2_cards.first().id)