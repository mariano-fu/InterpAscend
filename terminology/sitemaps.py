from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import (
    Medication, Diagnosis, MeSHTerm, FinancialTerm,
    GovernmentAgencyTerm, ImmigrationTerm, L2Term, L3Term, MedicareGlossaryTerm
)


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'
    
    def items(self):
        return ['terminology:translate', 'terminology:about_us', 'terminology:contact_us', 'terminology:privacy_policy']
    
    def location(self, item):
        return reverse(item)


class MedicationSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    
    def items(self):
        return Medication.objects.all()[:1000]  # Limit to 1000 for performance
    
    def lastmod(self, obj):
        return None  # No timestamp field available
    
    def location(self, obj):
        return reverse('terminology:medication_detail', args=[obj.id])


class DiagnosisSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    
    def items(self):
        return Diagnosis.objects.all()[:1000]
    
    def lastmod(self, obj):
        return None
    
    def location(self, obj):
        return reverse('terminology:diagnosis_detail', args=[obj.id])


class MeshSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    
    def items(self):
        return MeSHTerm.objects.all()[:1000]
    
    def lastmod(self, obj):
        return None
    
    def location(self, obj):
        return reverse('terminology:mesh_detail', args=[obj.id])


class FinancialSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    
    def items(self):
        return FinancialTerm.objects.all()[:1000]
    
    def lastmod(self, obj):
        return None
    
    def location(self, obj):
        return reverse('terminology:financial_detail', args=[obj.id])


class AgencySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    
    def items(self):
        return GovernmentAgencyTerm.objects.all()[:1000]
    
    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None
    
    def location(self, obj):
        return reverse('terminology:agency_detail', args=[obj.id])


class ImmigrationSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    
    def items(self):
        return ImmigrationTerm.objects.all()[:1000]
    
    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None
    
    def location(self, obj):
        return reverse('terminology:immigration_detail', args=[obj.id])


class L2Sitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    
    def items(self):
        return L2Term.objects.all()[:1000]
    
    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None
    
    def location(self, obj):
        return reverse('terminology:l2_detail', args=[obj.id])


class L3Sitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    
    def items(self):
        return L3Term.objects.all()[:1000]
    
    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None
    
    def location(self, obj):
        return reverse('terminology:l3_detail', args=[obj.id])


class MedicareSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    
    def items(self):
        return MedicareGlossaryTerm.objects.all()[:1000]
    
    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None
    
    def location(self, obj):
        return reverse('terminology:medicare_detail', args=[obj.id])