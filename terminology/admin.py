from django.contrib import admin
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

# Register your models here
@admin.register(MeSHTerm)
class MeSHTermAdmin(admin.ModelAdmin):
    list_display = ('english_term', 'spanish_term')
    search_fields = ('english_term', 'spanish_term')
    list_per_page = 50  # Increase items per page for faster navigation

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('english_name', 'spanish_name')
    search_fields = ('english_name', 'spanish_name')
    list_per_page = 50

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ('english_name', 'spanish_name')
    search_fields = ('english_name', 'spanish_name')
    list_per_page = 50

@admin.register(FinancialTerm)
class FinancialTermAdmin(admin.ModelAdmin):
    list_display = ('english_term', 'spanish_term')
    search_fields = ('english_term', 'spanish_term')
    list_per_page = 50

@admin.register(GovernmentAgencyTerm)
class GovernmentAgencyTermAdmin(admin.ModelAdmin):
    list_display = ('english_name', 'spanish_name', 'created_at', 'updated_at')
    search_fields = ('english_name', 'spanish_name')
    list_filter = ('created_at', 'updated_at')
    list_per_page = 50

@admin.register(ImmigrationTerm)
class ImmigrationTermAdmin(admin.ModelAdmin):
    list_display = ('english_term', 'spanish_term', 'created_at', 'updated_at')
    search_fields = ('english_term', 'spanish_term')
    list_filter = ('created_at', 'updated_at')
    list_per_page = 50

@admin.register(L2Term)
class L2TermAdmin(admin.ModelAdmin):
    list_display = ('english_term', 'spanish_term', 'created_at', 'updated_at')
    search_fields = ('english_term', 'spanish_term')
    list_filter = ('created_at', 'updated_at')
    list_per_page = 50

@admin.register(L3Term)
class L3TermAdmin(admin.ModelAdmin):
    list_display = ('english_term', 'spanish_term', 'created_at', 'updated_at')
    search_fields = ('english_term', 'spanish_term')
    list_filter = ('created_at', 'updated_at')
    list_per_page = 50

@admin.register(MedicareGlossaryTerm)
class MedicareGlossaryTermAdmin(admin.ModelAdmin):
    list_display = ('english_term', 'spanish_term', 'created_at', 'updated_at')
    search_fields = ('english_term', 'spanish_term')
    list_filter = ('created_at', 'updated_at')
    list_per_page = 50

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'updated_at', 'published')
    list_filter = ('published', 'author', 'created_at', 'updated_at')
    search_fields = ('title', 'content', 'author')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        ('Post Information', {
            'fields': ('title', 'title_es', 'author', 'slug', 'published')
        }),
        ('Content', {
            'fields': ('content', 'content_es', 'featured_image'),
            'classes': ('wide',)
        }),
    )
    list_editable = ('published',)
    date_hierarchy = 'created_at'
    
    class Media:
        css = {
            'all': ('https://cdn.quilljs.com/1.3.6/quill.snow.css',)
        }
        js = (
            'https://cdn.quilljs.com/1.3.6/quill.min.js',
            'terminology/js/quill_config.js',
        )


@admin.register(TermHelpfulness)
class TermHelpfulnessAdmin(admin.ModelAdmin):
    list_display = [
        'term_reference',
        'term_type',
        'is_helpful',
        'has_comment',
        'created_at',
        'session_id_short'
    ]
    list_filter = [
        'term_type',
        'is_helpful',
        'created_at',
        ('user_comment', admin.EmptyFieldListFilter),
    ]
    search_fields = ['term_reference', 'user_comment']
    readonly_fields = [
        'created_at',
        'session_id',
        'ip_address',
        'user_agent'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ('Feedback Information', {
            'fields': ('term_reference', 'term_type', 'term_id', 'is_helpful')
        }),
        ('User Input', {
            'fields': ('user_comment',)
        }),
        ('Metadata', {
            'fields': ('session_id', 'ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_comment(self, obj):
        return obj.has_comment
    has_comment.boolean = True
    has_comment.short_description = 'Has Comment'
    
    def session_id_short(self, obj):
        return obj.session_id[:8] + '...' if obj.session_id else ''
    session_id_short.short_description = 'Session'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    # Custom actions
    actions = ['mark_as_reviewed']
    
    def mark_as_reviewed(self, request, queryset):
        # This could be used to mark feedback as reviewed
        # For now, just a placeholder
        self.message_user(request, f"Marked {queryset.count()} feedback items as reviewed.")
    mark_as_reviewed.short_description = "Mark selected feedback as reviewed"

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('feedback_type', 'subject', 'created_at', 'status', 'email')
    list_filter = ('feedback_type', 'status', 'created_at')
    search_fields = ('subject', 'message', 'email', 'term_reference')
    readonly_fields = ('created_at',)
    list_editable = ('status',)
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Feedback Information', {
            'fields': ('feedback_type', 'subject', 'status')
        }),
        ('Content', {
            'fields': ('message', 'term_reference')
        }),
        ('Contact Information', {
            'fields': ('email', 'created_at')
        }),
    )
