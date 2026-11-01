import os
import sys
from urllib.parse import unquote
from django.conf import settings
from django.utils.text import slugify
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView

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
)
from .forms import MedicationSearchForm, FeedbackForm
from .llm_utils import translate_with_llm


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
