from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Category, Deck, DeckItem, UserCard, ReviewLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'slug', 
        'is_active', 
        'display_order', 
        'deck_count',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'display_order']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Display Settings', {
            'fields': ('display_order', 'icon_class', 'color_class')
        }),
        ('Visibility', {
            'fields': ('is_active',)
        }),
    )
    
    def deck_count(self, obj):
        """Show number of decks in this category"""
        count = obj.decks.count()
        if count > 0:
            url = reverse('admin:srs_deck_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} decks</a>', url, count)
        return '0 decks'
    deck_count.short_description = 'Decks'


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'created_by',
        'is_public',
        'is_active',
        'card_count',
        'active_users',
        'created_at'
    ]
    list_filter = [
        'category',
        'is_public',
        'is_active',
        'created_at',
        'created_by'
    ]
    search_fields = ['name', 'description']
    list_editable = ['is_public', 'is_active']
    ordering = ['category', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')
        }),
        ('Settings', {
            'fields': ('created_by', 'is_public', 'is_active')
        }),
    )
    
    def card_count(self, obj):
        """Show number of cards in this deck"""
        count = obj.get_card_count()
        if count > 0:
            url = reverse('admin:srs_deckitem_changelist') + f'?deck__id__exact={obj.id}'
            return format_html('<a href="{}">{} cards</a>', url, count)
        return '0 cards'
    card_count.short_description = 'Cards'
    
    def active_users(self, obj):
        """Show number of users studying this deck"""
        count = obj.get_active_users_count()
        return f'{count} users'
    active_users.short_description = 'Active Users'


@admin.register(DeckItem)
class DeckItemAdmin(admin.ModelAdmin):
    list_display = [
        'deck',
        'term_display',
        'content_type',
        'direction',
        'is_active',
        'user_count',
        'created_at'
    ]
    list_filter = [
        'deck__category',
        'deck',
        'content_type',
        'direction',
        'is_active',
        'created_at'
    ]
    search_fields = ['deck__name', 'note']
    list_editable = ['is_active']
    ordering = ['deck', 'created_at']
    
    fieldsets = (
        ('Card Information', {
            'fields': ('deck', 'content_type', 'object_id', 'direction')
        }),
        ('Additional Information', {
            'fields': ('note', 'is_active')
        }),
    )
    
    def term_display(self, obj):
        """Display the term this card represents"""
        if obj.term_content_object:
            return str(obj.term_content_object)[:50]
        return "Term not found"
    term_display.short_description = 'Term'
    
    def user_count(self, obj):
        """Show number of users studying this card"""
        count = obj.user_cards.count()
        if count > 0:
            url = reverse('admin:srs_usercard_changelist') + f'?deck_item__id__exact={obj.id}'
            return format_html('<a href="{}">{} users</a>', url, count)
        return '0 users'
    user_count.short_description = 'Users'


@admin.register(UserCard)
class UserCardAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'deck_item_display',
        'ease_factor',
        'interval',
        'repetitions',
        'due_status',
        'suspended',
        'last_reviewed'
    ]
    list_filter = [
        'deck_item__deck__category',
        'deck_item__deck',
        'suspended',
        'due',
        'last_reviewed'
    ]
    search_fields = [
        'user__username',
        'deck_item__deck__name'
    ]
    list_editable = ['suspended']
    ordering = ['due', 'user']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User & Card', {
            'fields': ('user', 'deck_item')
        }),
        ('SM-2 Algorithm State', {
            'fields': ('ease_factor', 'interval', 'repetitions', 'due')
        }),
        ('Progress Tracking', {
            'fields': ('lapses', 'suspended', 'last_reviewed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def deck_item_display(self, obj):
        """Display deck and term information"""
        return f"{obj.deck_item.deck.name} - {str(obj.deck_item.term_content_object)[:30]}"
    deck_item_display.short_description = 'Deck Item'
    
    def due_status(self, obj):
        """Show if card is due and when"""
        if obj.suspended:
            return format_html('<span style="color: orange;">Suspended</span>')
        elif obj.is_due():
            return format_html('<span style="color: red;">Due Now</span>')
        else:
            days = obj.days_until_due()
            if days == 0:
                return format_html('<span style="color: orange;">Due Today</span>')
            elif days == 1:
                return format_html('<span style="color: blue;">Due Tomorrow</span>')
            else:
                return format_html('<span style="color: green;">Due in {} days</span>', days)
    due_status.short_description = 'Status'


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'deck_item_display',
        'quality',
        'quality_text',
        'ease_factor',
        'interval',
        'reviewed_at',
        'latency_display'
    ]
    list_filter = [
        'quality',
        'deck_item__deck__category',
        'deck_item__deck',
        'reviewed_at',
        'user'
    ]
    search_fields = [
        'user__username',
        'deck_item__deck__name'
    ]
    ordering = ['-reviewed_at']
    readonly_fields = ['reviewed_at']
    date_hierarchy = 'reviewed_at'
    
    fieldsets = (
        ('Review Information', {
            'fields': ('user', 'deck_item', 'reviewed_at', 'quality')
        }),
        ('SM-2 State After Review', {
            'fields': ('ease_factor', 'interval', 'repetitions')
        }),
        ('Performance Metrics', {
            'fields': ('latency_ms', 'study_session_id')
        }),
    )
    
    def deck_item_display(self, obj):
        """Display deck and term information"""
        return f"{obj.deck_item.deck.name} - {str(obj.deck_item.term_content_object)[:30]}"
    deck_item_display.short_description = 'Deck Item'
    
    def quality_text(self, obj):
        """Show quality as text"""
        return obj.get_quality_display_text()
    quality_text.short_description = 'Quality Description'
    
    def latency_display(self, obj):
        """Display latency in a readable format"""
        if obj.latency_ms:
            if obj.latency_ms < 1000:
                return f"{obj.latency_ms}ms"
            else:
                return f"{obj.latency_ms/1000:.1f}s"
        return "N/A"
    latency_display.short_description = 'Response Time'
    
    # Custom actions
    actions = ['mark_as_successful', 'mark_as_failed']
    
    def mark_as_successful(self, request, queryset):
        """Mark selected reviews as successful (quality >= 3)"""
        count = queryset.filter(quality__lt=3).update(quality=4)
        self.message_user(request, f"Marked {count} reviews as successful.")
    mark_as_successful.short_description = "Mark selected reviews as successful"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected reviews as failed (quality < 3)"""
        count = queryset.filter(quality__gte=3).update(quality=1)
        self.message_user(request, f"Marked {count} reviews as failed.")
    mark_as_failed.short_description = "Mark selected reviews as failed"


# Custom admin site configuration
admin.site.site_header = "InterpAscend SRS Administration"
admin.site.site_title = "InterpAscend SRS Admin"
admin.site.index_title = "Spaced Repetition System Management"
