from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Extended user profile to store additional preferences and settings.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    email_notifications = models.BooleanField(
        default=False,
        help_text="Whether user wants to receive email notifications about updates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Category(models.Model):
    """
    Study categories that group related terminology types.
    Admin can edit names, descriptions, and visibility.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Display name for the category"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly version of the name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this category covers"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this category is visible to users"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which categories are displayed (lower numbers first)"
    )
    icon_class = models.CharField(
        max_length=50,
        default="fas fa-book",
        help_text="Font Awesome icon class for display"
    )
    color_class = models.CharField(
        max_length=20,
        default="primary",
        help_text="Bootstrap color class (primary, success, warning, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Deck(models.Model):
    """
    A collection of flashcards within a category.
    Can be created by admins or users (if allowed).
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='decks'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_decks'
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Whether this deck is available to all users"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this deck is currently available for study"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        unique_together = ['category', 'name']

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def get_card_count(self):
        """Return the number of cards in this deck"""
        return self.deck_items.count()

    def get_active_users_count(self):
        """Return the number of users who have studied this deck"""
        return User.objects.filter(user_cards__deck_item__deck=self).distinct().count()


class DeckItem(models.Model):
    """
    Individual flashcard linking to terminology models via GenericForeignKey.
    Supports different study directions (EN->ES, ES->EN).
    """
    DIRECTION_CHOICES = [
        ('EN_TO_ES', 'English to Spanish'),
        ('ES_TO_EN', 'Spanish to English'),
        ('BOTH', 'Both Directions'),
    ]

    deck = models.ForeignKey(
        Deck,
        on_delete=models.CASCADE,
        related_name='deck_items'
    )
    
    # Generic foreign key to terminology models
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    term_content_object = GenericForeignKey('content_type', 'object_id')
    
    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        default='BOTH',
        help_text="Study direction for this card"
    )
    
    note = models.TextField(
        blank=True,
        help_text="Optional additional information or context"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this card is available for study"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['deck', 'content_type', 'object_id', 'direction']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['deck', 'is_active']),
        ]

    def __str__(self):
        term_str = str(self.term_content_object) if self.term_content_object else "Unknown Term"
        return f"{self.deck.name} - {term_str} ({self.get_direction_display()})"

    def get_front_text(self):
        """Get the text to show on the front of the card based on direction"""
        if not self.term_content_object:
            return "Term not found"
            
        term = self.term_content_object
        
        def get_english_text(term_obj):
            """Get English text from term object, handling different field names"""
            return (getattr(term_obj, 'english_term', None) or
                    getattr(term_obj, 'english_name', None) or
                    str(term_obj))
        
        def get_spanish_text(term_obj):
            """Get Spanish text from term object, handling different field names"""
            return (getattr(term_obj, 'spanish_term', None) or
                    getattr(term_obj, 'spanish_name', None) or
                    getattr(term_obj, 'spanish_translation', None) or
                    'No Spanish translation available')
        
        if self.direction == 'EN_TO_ES':
            return get_english_text(term)
        elif self.direction == 'ES_TO_EN':
            return get_spanish_text(term)
        else:  # BOTH - default to English
            return get_english_text(term)

    def get_back_text(self):
        """Get the text to show on the back of the card based on direction"""
        if not self.term_content_object:
            return "Translation not found"
            
        term = self.term_content_object
        
        def get_english_text(term_obj):
            """Get English text from term object, handling different field names"""
            return (getattr(term_obj, 'english_term', None) or
                    getattr(term_obj, 'english_name', None) or
                    str(term_obj))
        
        def get_spanish_text(term_obj):
            """Get Spanish text from term object, handling different field names"""
            return (getattr(term_obj, 'spanish_term', None) or
                    getattr(term_obj, 'spanish_name', None) or
                    getattr(term_obj, 'spanish_translation', None) or
                    'No Spanish translation available')
        
        if self.direction == 'EN_TO_ES':
            return get_spanish_text(term)
        elif self.direction == 'ES_TO_EN':
            return get_english_text(term)
        else:  # BOTH - default to Spanish
            return get_spanish_text(term)


class UserCard(models.Model):
    """
    Tracks individual user progress on specific deck items using SM-2 algorithm.
    Each user has independent progress for each card.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_cards'
    )
    deck_item = models.ForeignKey(
        DeckItem,
        on_delete=models.CASCADE,
        related_name='user_cards'
    )
    
    # SM-2 Algorithm fields
    ease_factor = models.FloatField(
        default=2.5,
        validators=[MinValueValidator(1.3), MaxValueValidator(5.0)],
        help_text="SM-2 ease factor (1.3-5.0)"
    )
    interval = models.PositiveIntegerField(
        default=0,
        help_text="Days until next review"
    )
    repetitions = models.PositiveIntegerField(
        default=0,
        help_text="Number of successful repetitions"
    )
    due = models.DateTimeField(
        default=timezone.now,
        help_text="When this card is due for review"
    )
    
    # Additional tracking
    lapses = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this card was forgotten"
    )
    suspended = models.BooleanField(
        default=False,
        help_text="Whether this card is temporarily suspended from study"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_reviewed = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'deck_item']
        indexes = [
            models.Index(fields=['user', 'due']),
            models.Index(fields=['due', 'suspended']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.deck_item}"

    def is_due(self):
        """Check if this card is due for review"""
        return not self.suspended and self.due <= timezone.now()

    def days_until_due(self):
        """Calculate days until this card is due"""
        if self.suspended:
            return None
        delta = self.due - timezone.now()
        return max(0, delta.days)


class ReviewLog(models.Model):
    """
    Logs each review session for analytics and progress tracking.
    Stores the state before and after each review.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='review_logs'
    )
    deck_item = models.ForeignKey(
        DeckItem,
        on_delete=models.CASCADE,
        related_name='review_logs'
    )
    
    # Review details
    reviewed_at = models.DateTimeField(default=timezone.now)
    quality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Quality of response (0-5, where 0=total blackout, 5=perfect response)"
    )
    
    # SM-2 state after review
    ease_factor = models.FloatField(help_text="Ease factor after this review")
    interval = models.PositiveIntegerField(help_text="Interval after this review")
    repetitions = models.PositiveIntegerField(help_text="Repetitions after this review")
    
    # Performance metrics
    latency_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time taken to answer in milliseconds"
    )
    
    # Context
    study_session_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="ID to group reviews from the same study session"
    )

    class Meta:
        ordering = ['-reviewed_at']
        indexes = [
            models.Index(fields=['user', 'reviewed_at']),
            models.Index(fields=['deck_item', 'reviewed_at']),
            models.Index(fields=['quality', 'reviewed_at']),
            models.Index(fields=['study_session_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.deck_item} - Q{self.quality} ({self.reviewed_at.strftime('%Y-%m-%d %H:%M')})"

    def get_quality_display_text(self):
        """Get human-readable quality description"""
        quality_map = {
            0: "Total blackout",
            1: "Incorrect, easy to recall correct answer",
            2: "Incorrect, difficult to recall correct answer",
            3: "Correct with serious difficulty",
            4: "Correct response after hesitation",
            5: "Perfect response"
        }
        return quality_map.get(self.quality, "Unknown")

    def was_successful(self):
        """Check if this review was considered successful (quality >= 3)"""
        return self.quality >= 3
