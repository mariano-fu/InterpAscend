"""
URL configuration for interpascend1_1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
from terminology.sitemaps import (
    StaticViewSitemap, MedicationSitemap, DiagnosisSitemap, MeshSitemap,
    FinancialSitemap, AgencySitemap, ImmigrationSitemap, L2Sitemap,
    L3Sitemap, MedicareSitemap
)

# Sitemap configuration
sitemaps = {
    'static': StaticViewSitemap,
    'medications': MedicationSitemap,
    'diagnoses': DiagnosisSitemap,
    'mesh': MeshSitemap,
    'financial': FinancialSitemap,
    'agencies': AgencySitemap,
    'immigration': ImmigrationSitemap,
    'l2': L2Sitemap,
    'l3': L3Sitemap,
    'medicare': MedicareSitemap,
}

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Allow: /",
        "",
        "Sitemap: https://interpascend.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),
    path("terminology/", include("terminology.urls", namespace="terminology")),
    path("srs/", include("srs.urls", namespace="srs")),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt),
    path('', lambda request: redirect('/terminology/translate/', permanent=True)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
