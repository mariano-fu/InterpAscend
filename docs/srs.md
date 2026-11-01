# SRS (Spaced Repetition System) Documentation

## Overview

The SRS (Spaced Repetition System) is a comprehensive flashcard learning system integrated into InterpAscend. It implements the SM-2 algorithm for optimal spaced repetition scheduling, helping users learn medical, financial, immigration, and other terminology efficiently.

## Features

### Core Functionality
- **SM-2 Spaced Repetition Algorithm**: Scientifically-proven algorithm for optimal review scheduling
- **Multi-Category Support**: Study medical, financial, immigration, government, language learning, and healthcare terms
- **User Progress Tracking**: Individual progress tracking with comprehensive analytics
- **Real-time Statistics**: Live dashboard with study progress, success rates, and learning analytics
- **HTMX Integration**: Smooth, responsive study sessions without page refreshes
- **Text-to-Speech**: Built-in pronunciation support for English and Spanish terms
- **User Authentication**: Secure user accounts with isolated progress tracking

### Study Features
- **Quality-based Reviews**: Rate your recall with Again (1), Hard (3), Good (4), Easy (5)
- **Bidirectional Learning**: Study English→Spanish and Spanish→English
- **Session Management**: Track response times and study session analytics
- **Keyboard Shortcuts**: Efficient study with keyboard navigation
- **Progress Indicators**: Visual feedback on learning progress

## Architecture

### Models

#### Category
Organizes flashcards into logical groups (Medical, Financial, etc.)
```python
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
```

#### Deck
Collections of flashcards within a category
```python
class Deck(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category)
    created_by = models.ForeignKey(User)
    is_public = models.BooleanField(default=True)
```

#### DeckItem
Individual flashcards linking to terminology models
```python
class DeckItem(models.Model):
    deck = models.ForeignKey(Deck)
    term_content_type = models.ForeignKey(ContentType)
    term_object_id = models.PositiveIntegerField()
    term_content_object = GenericForeignKey('term_content_type', 'term_object_id')
    direction = models.CharField(max_length=10, choices=Direction.choices)
    note = models.TextField(blank=True)
```

#### UserCard
Tracks individual user progress on each flashcard
```python
class UserCard(models.Model):
    user = models.ForeignKey(User)
    deck_item = models.ForeignKey(DeckItem)
    ease_factor = models.FloatField(default=2.5)
    interval = models.IntegerField(default=0)
    repetitions = models.IntegerField(default=0)
    due = models.DateTimeField(default=timezone.now)
    lapses = models.IntegerField(default=0)
    suspended = models.BooleanField(default=False)
```

#### ReviewLog
Historical record of all review sessions
```python
class ReviewLog(models.Model):
    user = models.ForeignKey(User)
    deck_item = models.ForeignKey(DeckItem)
    reviewed_at = models.DateTimeField(default=timezone.now)
    quality = models.IntegerField()  # 0-5 scale
    ease_factor = models.FloatField()
    interval = models.IntegerField()
    repetitions = models.IntegerField()
    latency_ms = models.IntegerField(null=True, blank=True)
```

### SM-2 Algorithm Implementation

The system implements the SM-2 spaced repetition algorithm with the following parameters:

#### Quality Ratings
- **0-1 (Again)**: Incorrect response, reset repetitions
- **2-3 (Hard)**: Difficult recall, reduce ease factor
- **4 (Good)**: Correct response with effort
- **5 (Easy)**: Perfect recall, increase ease factor

#### Algorithm Parameters
- **Initial Ease Factor**: 2.5
- **Minimum Ease Factor**: 1.3
- **Initial Intervals**: 1 day, 6 days, then calculated
- **Ease Factor Adjustments**: Based on quality ratings

#### Implementation
```python
@dataclass
class SM2State:
    ease_factor: float
    interval: int
    repetitions: int

@dataclass
class SM2Result:
    ease_factor: float
    interval: int
    repetitions: int
    due_date: datetime

def sm2_update(state: SM2State, quality: int) -> SM2Result:
    # SM-2 algorithm implementation
    # Returns updated state and next due date
```

## API Reference

### Service Functions

#### `get_due_usercards(user, category_id=None, limit=50)`
Retrieves flashcards due for review
- **Parameters**:
  - `user`: Django User instance
  - `category_id`: Optional category filter
  - `limit`: Maximum cards to return
- **Returns**: QuerySet of UserCard objects

#### `ensure_usercards_exist(user, deck)`
Initializes UserCard objects for all DeckItems in a deck
- **Parameters**:
  - `user`: Django User instance
  - `deck`: Deck instance
- **Returns**: None (creates UserCard objects)

#### `review_card(user, deck_item_id, quality, reviewed_at=None, latency_ms=None)`
Processes a flashcard review and updates SM-2 state
- **Parameters**:
  - `user`: Django User instance
  - `deck_item_id`: ID of DeckItem being reviewed
  - `quality`: Quality rating (0-5)
  - `reviewed_at`: Optional review timestamp
  - `latency_ms`: Optional response time in milliseconds
- **Returns**: Dictionary with review results

#### `get_user_study_stats(user)`
Calculates comprehensive user statistics
- **Parameters**:
  - `user`: Django User instance
- **Returns**: Dictionary with statistics including:
  - `total_cards`: Total flashcards available
  - `due_cards`: Cards due for review
  - `new_cards`: Unreviewed cards
  - `young_cards`: Cards in learning phase
  - `mature_cards`: Well-learned cards
  - `success_rate`: Overall success percentage
  - `average_ease_factor`: Average difficulty rating
  - `study_streak`: Consecutive study days
  - `retention_estimate`: Estimated retention rate

#### `get_category_progress(user)`
Retrieves per-category progress statistics
- **Parameters**:
  - `user`: Django User instance
- **Returns**: List of dictionaries with category progress data

### URL Patterns

```python
urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    
    # Main Views
    path('', views.dashboard, name='dashboard'),
    path('categories/', views.category_list, name='category_list'),
    path('study/<slug:category_slug>/', views.study_session, name='study_session'),
    path('stats/', views.user_stats, name='user_stats'),
    
    # HTMX Endpoints
    path('study/<slug:category_slug>/next-card/', views.get_next_card, name='get_next_card'),
    path('study/<slug:category_slug>/show-answer/', views.show_answer, name='show_answer'),
    path('study/<slug:category_slug>/review/', views.review_card, name='review_card'),
]
```

## Usage Guide

### Getting Started

1. **Create Account**: Register at `/srs/signup/`
2. **Browse Categories**: View available study categories at `/srs/categories/`
3. **Start Studying**: Select a category to begin study session
4. **Review Cards**: Rate your recall using quality buttons
5. **Track Progress**: Monitor your learning at `/srs/stats/`

### Study Session Workflow

1. **Card Presentation**: System shows front of flashcard
2. **Recall Attempt**: Try to remember the translation
3. **Show Answer**: Click to reveal the correct answer
4. **Quality Rating**: Rate your recall:
   - **Again**: Didn't remember, need to see again soon
   - **Hard**: Remembered with difficulty
   - **Good**: Remembered correctly
   - **Easy**: Remembered easily
5. **Next Card**: System automatically loads next due card

### Keyboard Shortcuts

- **Space**: Show answer / Continue to next card
- **1**: Rate as "Again"
- **3**: Rate as "Hard"
- **4**: Rate as "Good"
- **5**: Rate as "Easy"

### Study Tips

1. **Daily Practice**: Study consistently for best results
2. **Honest Ratings**: Rate your actual recall difficulty
3. **Focus on Weak Areas**: System automatically prioritizes difficult cards
4. **Use Audio**: Click TTS buttons for pronunciation practice
5. **Track Progress**: Monitor your statistics to stay motivated

## Management Commands

### Create Demo Categories
```bash
python manage.py create_demo_categories
```
Creates sample categories and populates them with flashcards from existing terminology data.

### Available Categories
- **Medical**: Medical terminology (medications, diagnoses, MeSH terms)
- **Financial**: Financial terminology
- **Immigration**: Immigration-related terms
- **Government**: Government agency terms
- **Language Learning**: L2/L3 language learning terms
- **Healthcare**: Medicare and healthcare terms

## Admin Interface

### Category Management
- Create, edit, and deactivate categories
- Manage category descriptions and slugs
- Control category visibility

### Deck Management
- Create and organize flashcard decks
- Assign decks to categories
- Set deck visibility (public/private)

### User Progress Monitoring
- View user study statistics
- Monitor review logs and progress
- Identify struggling users or difficult cards

## Technical Details

### Database Schema
- **5 Core Models**: Category, Deck, DeckItem, UserCard, ReviewLog
- **Generic Foreign Keys**: Connect to any terminology model
- **Optimized Queries**: Efficient database access patterns
- **User Isolation**: Complete separation of user data

### Performance Considerations
- **Indexed Queries**: Optimized database indexes for fast lookups
- **Lazy Loading**: Efficient memory usage with QuerySet optimization
- **Caching**: Strategic caching of frequently accessed data
- **Batch Operations**: Efficient bulk operations for large datasets

### Security Features
- **User Authentication**: Required for all study features
- **Data Isolation**: Users can only access their own progress
- **CSRF Protection**: All forms protected against CSRF attacks
- **Input Validation**: Comprehensive validation of user inputs

## Integration with InterpAscend

### Terminology Models
The SRS integrates with all existing InterpAscend terminology models:
- `Medication` (english_name, spanish_name)
- `Diagnosis` (english_name, spanish_name)
- `MeSHTerm` (english_term, spanish_term)
- `FinancialTerm` (english_term, spanish_term)
- `GovernmentAgencyTerm` (english_name, spanish_name)
- `ImmigrationTerm` (english_term, spanish_term)
- `L2Term` (english_term, spanish_term)
- `L3Term` (english_term, spanish_term)
- `MedicareGlossaryTerm` (english_term, spanish_term)

### Template Integration
- Uses InterpAscend base template
- Consistent styling and navigation
- Responsive design for mobile devices
- HTMX integration for smooth interactions

### Authentication Integration
- Uses Django's built-in authentication
- Integrates with existing user system
- Supports user registration and login
- Session-based authentication

## Deployment

### Requirements
- Django 4.2+
- PostgreSQL (for production)
- HTMX (loaded via CDN)
- Chart.js (for analytics visualization)

### Settings Configuration
```python
INSTALLED_APPS = [
    # ... other apps
    'srs',
]

# Database configuration for Cloud Run
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # ... database configuration
    }
}
```

### Migration Commands
```bash
python manage.py makemigrations srs
python manage.py migrate
python manage.py create_demo_categories
```

### Static Files
- CSS: `srs/static/srs/css/`
- JavaScript: `srs/static/srs/js/`
- Templates: `srs/templates/srs/`

## Testing

### Test Coverage
- **Model Tests**: Complete model functionality and relationships
- **Algorithm Tests**: SM-2 algorithm accuracy and edge cases
- **Service Tests**: Business logic and data processing
- **View Tests**: HTTP responses and user interactions
- **Integration Tests**: End-to-end user workflows

### Running Tests
```bash
# Run all SRS tests
python manage.py test srs

# Run specific test modules
python manage.py test srs.test_models
python manage.py test srs.test_services
python manage.py test srs.test_views

# Run with verbose output
python manage.py test srs -v 2
```

## Troubleshooting

### Common Issues

#### No Cards Due
- **Cause**: All cards scheduled for future dates
- **Solution**: Wait for scheduled time or adjust card intervals

#### Slow Performance
- **Cause**: Large number of due cards or inefficient queries
- **Solution**: Implement pagination, optimize database queries

#### Authentication Issues
- **Cause**: Session expiration or login problems
- **Solution**: Clear browser cache, check authentication settings

#### Data Inconsistency
- **Cause**: Interrupted migrations or data corruption
- **Solution**: Run migrations, check database integrity

### Debug Mode
Enable Django debug mode for detailed error information:
```python
DEBUG = True  # Only for development
```

### Logging
Configure logging for SRS operations:
```python
LOGGING = {
    'loggers': {
        'srs': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

## Future Enhancements

### Planned Features
- **Mobile App**: Native mobile application
- **Offline Support**: Study without internet connection
- **Advanced Analytics**: Detailed learning analytics
- **Social Features**: Study groups and leaderboards
- **Custom Decks**: User-created flashcard decks
- **Import/Export**: Deck sharing and backup features

### API Extensions
- **REST API**: Full REST API for mobile apps
- **Bulk Operations**: Efficient bulk card operations
- **Advanced Filtering**: Complex query capabilities
- **Real-time Updates**: WebSocket support for live updates

## Support

### Documentation
- **API Reference**: Complete API documentation
- **User Guide**: Step-by-step usage instructions
- **Developer Guide**: Technical implementation details

### Community
- **GitHub Issues**: Bug reports and feature requests
- **Discussion Forum**: Community support and discussions
- **Documentation Wiki**: Community-maintained documentation

### Contact
For technical support or questions about the SRS system, please contact the InterpAscend development team.