import os
import sys
import json
from urllib.parse import unquote
from django.conf import settings
from django.utils.text import slugify
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import IntegrityError

from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0

from .models import (
    Medication,
    Diagnosis,
    MeSHTerm,
    FinancialTerm,
    GovernmentAgencyTerm,
    ImmigrationTerm,
    L2Term,
    L3Term,
    MedicareGlossaryTerm,
    BlogPost,
    Feedback,
    TermHelpfulness,
)
from .forms import MedicationSearchForm, FeedbackForm
from .llm_utils import translate_with_llm


def build_tts_context(obj, en_field, es_field):
    """
    Builds audio_en and audio_es paths if TTS files exist for the given object fields.
    en_field: attribute name for English text
    es_field: attribute name for Spanish text
    """
    context = {}
    tts_dir = os.path.join(settings.BASE_DIR, 'terminology', 'static', 'terminology', 'tts')

    # English pronunciation
    en_text = getattr(obj, en_field, None)
    if en_text:
        en_slug = slugify(en_text)
        en_filename = f"{en_slug}_en.mp3"
        if os.path.exists(os.path.join(tts_dir, en_filename)):
            context['audio_en'] = f"terminology/tts/{en_filename}"

    # Spanish pronunciation
    es_text = getattr(obj, es_field, None)
    if es_text:
        es_slug = slugify(es_text)
        es_filename = f"{es_slug}_es.mp3"
        if os.path.exists(os.path.join(tts_dir, es_filename)):
            context['audio_es'] = f"terminology/tts/{es_filename}"

    return context


class MedicationDetailView(DetailView):
    model = Medication
    template_name = 'terminology/medication_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_tts_context(self.object, 'english_name', 'spanish_name'))
        return context


class DiagnosisDetailView(DetailView):
    model = Diagnosis
    template_name = 'terminology/diagnosis_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_tts_context(self.object, 'english_name', 'spanish_name'))
        return context


class MeSHTermDetailView(DetailView):
    model = MeSHTerm
    template_name = 'terminology/mesh_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_tts_context(self.object, 'english_term', 'spanish_term'))
        return context


class FinancialTermDetailView(DetailView):
    model = FinancialTerm
    template_name = 'terminology/financial_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_tts_context(self.object, 'english_term', 'spanish_term'))
        return context


class GovernmentAgencyTermDetailView(DetailView):
    model = GovernmentAgencyTerm
    template_name = 'terminology/gov_agency.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_tts_context(self.object, 'english_name', 'spanish_name'))
        return context


class ImmigrationTermDetailView(DetailView):
    model = ImmigrationTerm
    template_name = 'terminology/immigration_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_tts_context(self.object, 'english_term', 'spanish_term'))
        return context


class L2TermDetailView(DetailView):
    model = L2Term
    template_name = 'terminology/l2_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_tts_context(self.object, 'english_term', 'spanish_term'))
        return context


class L3TermDetailView(DetailView):
    model = L3Term
    template_name = 'terminology/l3_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_tts_context(self.object, 'english_term', 'spanish_term'))
        return context


class MedicareGlossaryTermDetailView(DetailView):
    model = MedicareGlossaryTerm
    template_name = 'terminology/medicare_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_tts_context(self.object, 'english_term', 'spanish_term'))
        return context


def translate_medication(request):
    form = MedicationSearchForm(request.GET or None)

    med_results = []
    diag_results = []
    mesh_results = []
    financial_results = []
    agency_results = []
    immigration_results = []
    l2_results = []
    l3_results = []
    medicare_results = []     # ← added
    llm_results = []

    match_type = request.GET.get('match_type', 'contains')

    if form.is_valid():
        q = form.cleaned_data['query'].strip()

        # --- language detection (unchanged) ---
        def detect_language_robust(text):
            text_lower = text.lower()
            spanish_indicators = [
                'ñ','á','é','í','ó','ú','ü',
                ' de ',' del ',' la ', 'el', 'los', 'las',
                'con', 'por', 'para', 'sin'
            ]
            english_indicators = [
                ' the ',' and ',' of ',' to ',
                ' for ',' with ',' without '
            ]
            spanish_score = sum(ind in text_lower for ind in spanish_indicators)
            english_score = sum(ind in text_lower for ind in english_indicators)
            if spanish_score > english_score:
                return 'es'
            if english_score > spanish_score:
                return 'en'
            try:
                return detect(text)
            except:
                return 'en'

        lang = detect_language_robust(q)
        src_lang, dest_lang = ('es', 'en') if lang == 'es' else ('en', 'es')
        print(f"DEBUG: Query='{q}', src_lang='{src_lang}', dest_lang='{dest_lang}'", file=sys.stderr)

        # --- lookup type ---
        if match_type == 'exact':
            lookup = 'iexact'
        elif match_type == 'startswith':
            lookup = 'istartswith'
        else:
            lookup = 'icontains'

        def q_kwargs(field):
            return {f"{field}__{lookup}": q}

        # --- global dedupe set for all lists ---
        seen = set()

        # 1) Medications
        for m in Medication.objects.filter(
                Q(**q_kwargs('english_name')) | Q(**q_kwargs('spanish_name'))):
            inp = m.english_name if src_lang == 'en' else m.spanish_name
            out = m.spanish_name if src_lang == 'en' else m.english_name
            key = (inp.lower().strip(), out.lower().strip())
            if key in seen: continue
            seen.add(key)
            med_results.append({'id': m.id, 'input': inp, 'output': out})

        # 2) Diagnoses
        for d in Diagnosis.objects.filter(
                Q(**q_kwargs('english_name')) | Q(**q_kwargs('spanish_name'))):
            inp = d.english_name if src_lang == 'en' else d.spanish_name
            out = d.spanish_name if src_lang == 'en' else d.english_name
            key = (inp.lower().strip(), out.lower().strip())
            if key in seen: continue
            seen.add(key)
            diag_results.append({'id': d.id, 'input': inp, 'output': out})

        # 3) MeSH Terms
        for mesh in MeSHTerm.objects.filter(
                Q(**q_kwargs('english_term')) | Q(**q_kwargs('spanish_term'))):
            inp = mesh.english_term if src_lang == 'en' else mesh.spanish_term
            out = mesh.spanish_term if src_lang == 'en' else mesh.english_term
            key = (inp.lower().strip(), out.lower().strip())
            if key in seen: continue
            seen.add(key)
            mesh_results.append({'id': mesh.id, 'input': inp, 'output': out})

        # 4) Financial Terms
        for ft in FinancialTerm.objects.filter(
                Q(**q_kwargs('english_term')) | Q(**q_kwargs('spanish_term'))):
            inp = ft.english_term if src_lang == 'en' else ft.spanish_term
            out = ft.spanish_term if src_lang == 'en' else ft.english_term
            key = (inp.lower().strip(), out.lower().strip())
            if key in seen: continue
            seen.add(key)
            financial_results.append({'id': ft.id, 'input': inp, 'output': out})

        # 5) Government Agencies
        for ag in GovernmentAgencyTerm.objects.filter(
                Q(**q_kwargs('english_name')) | Q(**q_kwargs('spanish_name'))):
            inp = ag.english_name if src_lang == 'en' else ag.spanish_name
            out = ag.spanish_name if src_lang == 'en' else ag.english_name
            key = (inp.lower().strip(), out.lower().strip())
            if key in seen: continue
            seen.add(key)
            agency_results.append({'id': ag.id, 'input': inp, 'output': out})

        # 6) Immigration Terms
        for imm in ImmigrationTerm.objects.filter(
                Q(**q_kwargs('english_term')) | Q(**q_kwargs('spanish_term'))):
            inp = imm.english_term if src_lang == 'en' else imm.spanish_term
            out = imm.spanish_term if src_lang == 'en' else imm.english_term
            key = (inp.lower().strip(), out.lower().strip())
            if key in seen: continue
            seen.add(key)
            immigration_results.append({
                'id': imm.id,
                'input': inp,
                'output': out
            })

        # 7) L2 Terms
        for term in L2Term.objects.filter(
                Q(**q_kwargs('english_term')) | Q(**q_kwargs('spanish_term'))):
            inp = term.english_term if src_lang == 'en' else term.spanish_term
            out = term.spanish_term if src_lang == 'en' else term.english_term
            key = (inp.lower().strip(), out.lower().strip())
            if key in seen: continue
            seen.add(key)
            l2_results.append({
                'id': term.id,
                'input': inp,
                'output': out
            })

        # 8) L3 Terms
        for term in L3Term.objects.filter(
                Q(**q_kwargs('english_term')) | Q(**q_kwargs('spanish_term'))):
            inp = term.english_term if src_lang == 'en' else term.spanish_term
            out = term.spanish_term if src_lang == 'en' else term.english_term
            key = (inp.lower().strip(), out.lower().strip())
            if key in seen: continue
            seen.add(key)
            l3_results.append({
                'id': term.id,
                'input': inp,
                'output': out
            })

        # 9) Medicare Glossary Terms
        for mt in MedicareGlossaryTerm.objects.filter(
                Q(**q_kwargs('english_term')) | Q(**q_kwargs('spanish_term'))):
            inp = mt.english_term if src_lang == 'en' else mt.spanish_term
            out = mt.spanish_term if src_lang == 'en' else mt.english_term
            key = (inp.lower().strip(), out.lower().strip())
            if key in seen: continue
            seen.add(key)
            medicare_results.append({'id': mt.id, 'input': inp, 'output': out})

        # LLM fallback if nothing local
        total_local = (
            len(med_results) + len(diag_results) + len(mesh_results) +
            len(financial_results) + len(agency_results) +
            len(immigration_results) + len(l2_results) + len(l3_results) +
            len(medicare_results)    # include medicare in the count
        )
        if total_local == 0:
            llm_translations = translate_with_llm(
                phrase=q,
                local_translations={},
                src_lang=src_lang,
                dest_lang=dest_lang,
                model="gpt-3.5-turbo"
            )
            # Convert LLM string results to the same format as other results
            for translation in llm_translations:
                llm_results.append({
                    'input': q,  # Original query
                    'output': translation,  # LLM translation
                    'id': None  # No database ID for LLM results
                })

    # Get recent blog posts for the "Latest Updates" section
    recent_posts = BlogPost.objects.filter(published=True).order_by('-created_at')[:3]
    
    return render(request, 'terminology/translate.html', {
        'form': form,
        'med_results': med_results,
        'diag_results': diag_results,
        'mesh_results': mesh_results,
        'financial_results': financial_results,
        'agency_results': agency_results,
        'immigration_results': immigration_results,
        'l2_results': l2_results,
        'l3_results': l3_results,
        'medicare_results': medicare_results,  # ← pass into context
        'llm_results': llm_results,
        'match_type': match_type,
        'recent_posts': recent_posts,  # ← add recent blog posts
    })


def llm_detail(request, term):
    # The 'term' parameter is the translation (what was clicked)
    clicked_term = unquote(term)
    tts_dir = os.path.join(settings.BASE_DIR, 'terminology', 'static', 'terminology', 'tts')
    
    # Get the original search term
    original_query = request.GET.get('query', '')
    original_input = request.GET.get('input', '')
    
    # Use a robust language detection function (similar to the one in translate_medication view)
    def detect_language_robust(text):
        text_lower = text.lower()
        spanish_indicators = [
            'ñ','á','é','í','ó','ú','ü',
            ' de ',' del ',' la ', 'el', 'los', 'las',
            'con', 'por', 'para', 'sin'
        ]
        english_indicators = [
            ' the ',' and ',' of ',' to ',
            ' for ',' with ',' without '
        ]
        spanish_score = sum(ind in text_lower for ind in spanish_indicators)
        english_score = sum(ind in text_lower for ind in english_indicators)
        if spanish_score > english_score:
            return 'es'
        if english_score > spanish_score:
            return 'en'
        try:
            from langdetect import detect
            return detect(text)
        except:
            return 'en'
    
    # Determine the language of the original input
    input_term = original_input if original_input else original_query
    if input_term:
        input_lang = detect_language_robust(input_term)
        
        # Set up the terms based on the detected input language
        if input_lang == 'en':
            english_term = input_term
            spanish_term = clicked_term
            src_lang = 'en'
            dest_lang = 'es'
        else:
            english_term = clicked_term
            spanish_term = input_term
            src_lang = 'es'
            dest_lang = 'en'
    else:
        # Fallback: assume the clicked term is Spanish (most common case)
        english_term = original_query if original_query else 'Unknown'
        spanish_term = clicked_term
        src_lang = 'en'
        dest_lang = 'es'
    
    mock_object = type('MockObject', (), {
        'english_name': english_term,
        'spanish_name': spanish_term,
        'text': input_term,  # The original search term (displayed prominently)
        'translation': clicked_term,  # The translation
        'language': src_lang,  # Language of the original search term
        'translation_language': dest_lang  # Language of the translation
    })()
    
    context = {
        'object': mock_object,
        'term': mock_object,  # For compatibility with term_detail.html if needed
        'clicked_term': clicked_term,
        'original_term': input_term,
        'src_lang': src_lang,
        'dest_lang': dest_lang,
    }

    en_filename = f"{slugify(english_term)}_en.mp3"
    if os.path.exists(os.path.join(tts_dir, en_filename)):
        context['audio_en'] = f"terminology/tts/{en_filename}"
    
    es_filename = f"{slugify(spanish_term)}_es.mp3"
    if os.path.exists(os.path.join(tts_dir, es_filename)):
        context['audio_es'] = f"terminology/tts/{es_filename}"

    return render(request, 'terminology/llm_detail.html', context)


def about_us(request):
    """About Us page view"""
    return render(request, 'terminology/about_us.html')


def contact_us(request):
    """Contact Us page view"""
    return render(request, 'terminology/contact_us.html')


def privacy_policy(request):
    """Privacy Policy page view"""
    return render(request, 'terminology/privacy_policy.html')

def blog_list(request):
    """Blog listing page view"""
    posts = BlogPost.objects.filter(published=True).order_by('-created_at')
    return render(request, 'terminology/blog_list.html', {'posts': posts})

def blog_detail(request, slug):
    """Blog post detail page view"""
    post = get_object_or_404(BlogPost, slug=slug, published=True)
    return render(request, 'terminology/blog_detail.html', {'post': post})

def feedback(request):
    """Feedback form view"""
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'terminology/feedback_success.html')
    else:
        form = FeedbackForm()
    return render(request, 'terminology/feedback.html', {'form': form})


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@require_http_methods(["POST"])
def submit_term_feedback(request):
    """AJAX endpoint for submitting term helpfulness feedback"""
    try:
        # Parse JSON data
        data = json.loads(request.body)
        
        # Extract feedback data
        is_helpful = data.get('is_helpful')
        term_reference = data.get('term_reference')
        term_type = data.get('term_type')
        term_id = data.get('term_id')
        user_comment = data.get('user_comment', '').strip()
        
        # Validate required fields
        if is_helpful is None or not term_reference or not term_type:
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required fields.'
            }, status=400)
        
        # Get or create session ID
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key
        
        # Create feedback record
        feedback = TermHelpfulness.objects.create(
            is_helpful=bool(is_helpful),
            term_reference=term_reference,
            term_type=term_type,
            term_id=term_id if term_id else None,
            user_comment=user_comment if user_comment else None,
            session_id=session_id,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:1000]  # Truncate long user agents
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Thank you for your feedback! Your input helps us improve our terminology database.',
            'feedback_id': feedback.id
        })
        
    except IntegrityError:
        return JsonResponse({
            'status': 'error',
            'message': 'You have already provided feedback for this term.'
        }, status=409)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request format.'
        }, status=400)
    except Exception as e:
        # Log the error in production
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Feedback submission error: {str(e)}")
        
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while processing your feedback. Please try again.'
        }, status=500)
