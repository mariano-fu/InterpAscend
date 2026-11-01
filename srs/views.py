from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
from .forms import CustomUserCreationForm
from .models import UserProfile
import json
import uuid
import logging
from datetime import datetime

# Custom login_required decorator for SRS views
def srs_login_required(view_func):
    """Custom login_required decorator that redirects to SRS login page"""
    from django.contrib.auth.decorators import user_passes_test
    from django.shortcuts import redirect
    from django.urls import reverse
    
    def check_login(user):
        return user.is_authenticated
    
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('srs:login')}?next={request.get_full_path()}")
        return view_func(request, *args, **kwargs)
    
    return wrapper

logger = logging.getLogger(__name__)


class SignUpView(CreateView):
    """User registration view with email and notifications support"""
    form_class = CustomUserCreationForm
    template_name = 'srs/auth/signup.html'
    success_url = reverse_lazy('srs:dashboard')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Update the user's profile with email notifications preference
        email_notifications = form.cleaned_data.get('email_notifications', False)
        if hasattr(self.object, 'profile'):
            self.object.profile.email_notifications = email_notifications
            self.object.profile.save()
        else:
            # Create profile if it doesn't exist (fallback)
            UserProfile.objects.create(
                user=self.object,
                email_notifications=email_notifications
            )
        
        # Log the user in after successful registration
        login(self.request, self.object)
        
        # Customize welcome message based on email notifications preference
        if email_notifications:
            messages.success(
                self.request,
                'Welcome to InterpAscend! Your account has been created successfully. '
                'You\'ll receive email updates about new features and content.'
            )
        else:
            messages.success(
                self.request,
                'Welcome to InterpAscend! Your account has been created successfully.'
            )
        
        return response


@srs_login_required
def dashboard(request):
    """Main SRS dashboard - shows user's study progress and available categories"""
    # This will be implemented in later phases
    context = {
        'user': request.user,
        'page_title': 'Study Dashboard',
    }
    return render(request, 'srs/dashboard.html', context)


@srs_login_required
def category_list(request):
    """List all available study categories"""
    from .models import Category
    from .services import get_due_usercards, ensure_usercards_exist
    
    # Get all active categories
    categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')
    
    # Get category stats for the current user
    category_stats = []
    for category in categories:
        # Get decks in this category
        decks = category.decks.filter(is_active=True, is_public=True)
        
        # Initialize user cards for all decks in this category
        total_new_cards = 0
        for deck in decks:
            total_new_cards += ensure_usercards_exist(request.user, deck)
        
        # Get due cards for this category
        due_cards = get_due_usercards(request.user, category.id, limit=1000)
        due_count = len(due_cards)
        
        # Get total cards for this category
        from .models import UserCard
        total_cards = UserCard.objects.filter(
            user=request.user,
            deck_item__deck__category=category
        ).count()
        
        category_stats.append({
            'category': category,
            'due_count': due_count,
            'total_cards': total_cards,
            'new_cards': total_new_cards,
            'deck_count': decks.count()
        })
    
    context = {
        'page_title': 'Study Categories',
        'category_stats': category_stats,
    }
    return render(request, 'srs/category_list.html', context)


@srs_login_required
def study_session(request, category_slug):
    """Study session for a specific category"""
    from .models import Category
    from .services import get_due_usercards, ensure_usercards_exist
    
    # Get the category
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    
    # Ensure user cards exist for all decks in this category
    for deck in category.decks.filter(is_active=True, is_public=True):
        ensure_usercards_exist(request.user, deck)
    
    # Get due cards for this category
    due_cards = get_due_usercards(request.user, category.id, limit=50)
    
    # Generate a study session ID
    study_session_id = str(uuid.uuid4())[:8]
    
    context = {
        'category': category,
        'category_slug': category_slug,
        'page_title': f'Study {category.name}',
        'due_cards_count': len(due_cards),
        'study_session_id': study_session_id,
        'has_cards': len(due_cards) > 0,
    }
    return render(request, 'srs/study_session.html', context)


@srs_login_required
def get_next_card(request, category_slug):
    """HTMX endpoint to get the next card for study"""
    from .models import Category
    from .services import get_due_usercards
    
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    due_cards = get_due_usercards(request.user, category.id, limit=1)
    
    if not due_cards:
        # No more cards due
        context = {
            'category': category,
            'no_cards_due': True,
        }
        return render(request, 'srs/partials/no_cards_due.html', context)
    
    card = due_cards[0]
    deck_item = card.deck_item
    term = deck_item.term_content_object
    
    # Determine front and back based on direction with robust field detection
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
    
    if deck_item.direction == 'EN_TO_ES':
        front_text = get_english_text(term)
        back_text = get_spanish_text(term)
        front_lang = 'en'
        back_lang = 'es'
    else:  # ES_TO_EN
        front_text = get_spanish_text(term)
        back_text = get_english_text(term)
        front_lang = 'es'
        back_lang = 'en'
    
    # Get additional context (definition, notes, etc.)
    definition = getattr(term, 'definition', getattr(term, 'description', ''))
    notes = deck_item.note or ''
    
    context = {
        'card': card,
        'deck_item': deck_item,
        'term': term,
        'front_text': front_text,
        'back_text': back_text,
        'front_lang': front_lang,
        'back_lang': back_lang,
        'definition': definition,
        'notes': notes,
        'category': category,
        'show_front': True,
    }
    return render(request, 'srs/partials/flashcard.html', context)


@srs_login_required
def show_answer(request, category_slug):
    """HTMX endpoint to show the answer side of the card"""
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    # Handle both JSON and form data
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            deck_item_id = data.get('deck_item_id')
        else:
            # Handle form data from HTMX
            deck_item_id = request.POST.get('deck_item_id')
        
        if not deck_item_id:
            return HttpResponse(status=400)
            
    except (json.JSONDecodeError, KeyError, ValueError):
        return HttpResponse(status=400)
    
    from .models import Category, DeckItem
    
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    deck_item = get_object_or_404(DeckItem, id=deck_item_id, is_active=True)
    
    # Get the user card
    from .models import UserCard
    try:
        card = UserCard.objects.get(user=request.user, deck_item=deck_item)
    except UserCard.DoesNotExist:
        return HttpResponse(status=404)
    
    term = deck_item.term_content_object
    
    # Determine front and back based on direction with robust field detection
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
    
    if deck_item.direction == 'EN_TO_ES':
        front_text = get_english_text(term)
        back_text = get_spanish_text(term)
        front_lang = 'en'
        back_lang = 'es'
    else:  # ES_TO_EN
        front_text = get_spanish_text(term)
        back_text = get_english_text(term)
        front_lang = 'es'
        back_lang = 'en'
    
    # Debug logging to help track down translation issues
    logger.debug(f"Flashcard show_answer - Term: {term.__class__.__name__}, Direction: {deck_item.direction}")
    logger.debug(f"Front text: '{front_text}', Back text: '{back_text}'")
    logger.debug(f"Term fields: english_term={getattr(term, 'english_term', 'N/A')}, "
                f"english_name={getattr(term, 'english_name', 'N/A')}, "
                f"spanish_term={getattr(term, 'spanish_term', 'N/A')}, "
                f"spanish_name={getattr(term, 'spanish_name', 'N/A')}")
    
    # Get additional context
    definition = getattr(term, 'definition', getattr(term, 'description', ''))
    notes = deck_item.note or ''
    
    context = {
        'card': card,
        'deck_item': deck_item,
        'term': term,
        'front_text': front_text,
        'back_text': back_text,
        'front_lang': front_lang,
        'back_lang': back_lang,
        'definition': definition,
        'notes': notes,
        'category': category,
        'show_front': False,
        'show_answer': True,
    }
    return render(request, 'srs/partials/flashcard.html', context)


@srs_login_required
@require_POST
def review_card(request, category_slug):
    """HTMX endpoint to process a card review"""
    try:
        data = json.loads(request.body)
        deck_item_id = data.get('deck_item_id')
        quality = int(data.get('quality'))
        study_session_id = data.get('study_session_id')
        response_time_ms = data.get('response_time_ms')
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return JsonResponse({'error': 'Invalid request data'}, status=400)
    
    if quality not in range(6):  # 0-5
        return JsonResponse({'error': 'Invalid quality rating'}, status=400)
    
    from .services import review_card as process_review
    
    try:
        result = process_review(
            user=request.user,
            deck_item_id=deck_item_id,
            quality=quality,
            latency_ms=response_time_ms,
            study_session_id=study_session_id
        )
        
        if result['success']:
            # Return success response with next due info
            return JsonResponse({
                'success': True,
                'next_due': result['next_due'].isoformat(),
                'interval_description': result['interval_description'],
                'was_successful': result['was_successful'],
            })
        else:
            return JsonResponse({'error': 'Review processing failed'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@srs_login_required
def user_stats(request):
    """User statistics and progress dashboard"""
    from .services import get_user_study_stats, get_category_progress
    from .models import Category, ReviewLog
    from django.utils import timezone
    from datetime import timedelta
    import json
    
    # Get overall user statistics
    overall_stats = get_user_study_stats(request.user)
    
    # Get per-category progress
    category_progress = get_category_progress(request.user)
    
    # Get recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_reviews = ReviewLog.objects.filter(
        user=request.user,
        reviewed_at__gte=thirty_days_ago
    ).order_by('-reviewed_at')[:50]
    
    # Calculate daily review counts for the last 30 days
    daily_reviews = {}
    for i in range(30):
        date = (timezone.now() - timedelta(days=i)).date()
        daily_reviews[date.isoformat()] = 0
    
    for review in ReviewLog.objects.filter(
        user=request.user,
        reviewed_at__gte=thirty_days_ago
    ):
        date_key = review.reviewed_at.date().isoformat()
        if date_key in daily_reviews:
            daily_reviews[date_key] += 1
    
    # Prepare chart data
    chart_data = {
        'daily_reviews': {
            'labels': list(daily_reviews.keys())[-14:],  # Last 14 days
            'data': list(daily_reviews.values())[-14:]
        },
        'category_progress': {
            'labels': [cp['category'].name for cp in category_progress],
            'total_cards': [cp['total_cards'] for cp in category_progress],
            'due_cards': [cp['due_cards'] for cp in category_progress],
            'success_rates': [cp['success_rate'] for cp in category_progress]
        }
    }
    
    context = {
        'page_title': 'Your Progress',
        'overall_stats': overall_stats,
        'category_progress': category_progress,
        'recent_reviews': recent_reviews,
        'chart_data_json': json.dumps(chart_data),
        'chart_data': chart_data,
    }
    return render(request, 'srs/user_stats.html', context)
