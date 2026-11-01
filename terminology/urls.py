# terminology/urls.py

from django.urls import path
from .views import (
    translate_medication,
    MedicationDetailView,
    DiagnosisDetailView,
    MeSHTermDetailView,
    FinancialTermDetailView,
    GovernmentAgencyTermDetailView,
    ImmigrationTermDetailView,
    L2TermDetailView,
    L3TermDetailView,
    llm_detail,
    MedicareGlossaryTermDetailView,
    about_us,
    contact_us,
    privacy_policy,
    blog_list,
    blog_detail,
    feedback,
    submit_term_feedback,
)
from .views_favorites import (
    favorites_page,
    favorites_api,
    favorites_export,
)

app_name = "terminology"

urlpatterns = [
    # Detail pages
    path("medication/<int:pk>/",      MedicationDetailView.as_view(),             name="medication_detail"),
    path("diagnosis/<int:pk>/",       DiagnosisDetailView.as_view(),             name="diagnosis_detail"),
    path("mesh/<int:pk>/",            MeSHTermDetailView.as_view(),               name="mesh_detail"),
    path("financial/<int:pk>/",       FinancialTermDetailView.as_view(),          name="financial_detail"),
    path("agency/<int:pk>/",          GovernmentAgencyTermDetailView.as_view(),   name="agency_detail"),
    path("immigration/<int:pk>/",     ImmigrationTermDetailView.as_view(),        name="immigration_detail"),
    path("l2/<int:pk>/",              L2TermDetailView.as_view(),                 name="l2_detail"),
    path("l3/<int:pk>/",              L3TermDetailView.as_view(),                 name="l3_detail"),
    path("llm/<str:term>/",           llm_detail,                                 name="llm_detail"),
    path("medicare/<int:pk>/",        MedicareGlossaryTermDetailView.as_view(),  name="medicare_detail"),

    # Translate/search page
    path("translate/", translate_medication,             name="translate"),
    
    # Favorites functionality
    path("favorites/", favorites_page, name="favorites_page"),
    path("api/favorites/", favorites_api, name="favorites_api"),
    path("api/favorites/export/", favorites_export, name="favorites_export"),
    
    # Blog pages
    path("blog/", blog_list, name="blog_list"),
    path("blog/<slug:slug>/", blog_detail, name="blog_detail"),

    # Info pages
    path("about/", about_us, name="about_us"),
    path("contact/", contact_us, name="contact_us"),
    path("privacy/", privacy_policy, name="privacy_policy"),
    path("feedback/", feedback, name="feedback"),
    path("feedback/submit/", submit_term_feedback, name="submit_term_feedback"),
]
