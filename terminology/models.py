from django.db import models

class Medication(models.Model):
    english_name    = models.CharField(max_length=200)
    spanish_name    = models.CharField(max_length=200, blank=True, null=True)
    english_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for English term")
    spanish_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for Spanish term")

    def __str__(self):
        return self.english_name or self.spanish_name or "Unnamed Medication"

class Diagnosis(models.Model):
    english_name = models.CharField(max_length=200)
    spanish_name = models.CharField(max_length=200, blank=True, null=True)
    english_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for English term")
    spanish_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for Spanish term")

    def __str__(self):
        return self.english_name or self.spanish_name or "Unnamed Diagnosis"

class MeSHTerm(models.Model):
    english_term = models.CharField(max_length=200)
    spanish_term = models.CharField(max_length=200, blank=True, null=True)
    english_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for English term")
    spanish_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for Spanish term")

    def __str__(self):
        return self.english_term or self.spanish_term or "Unnamed MeSHTerm"
class FinancialTerm(models.Model):
    english_term = models.CharField(max_length=200)
    spanish_term = models.CharField(max_length=200, blank=True, null=True)
    english_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for English term")
    spanish_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for Spanish term")

    def __str__(self):
        return self.english_term
class GovernmentAgencyTerm(models.Model):
    english_name = models.CharField(max_length=200)
    spanish_name = models.CharField(max_length=200, blank=True, null=True)
    english_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for English term")
    spanish_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for Spanish term")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.english_name or self.spanish_name or "Unnamed Agency"
class ImmigrationTerm(models.Model):
    english_term = models.CharField(max_length=200, unique=True)
    spanish_term = models.CharField(max_length=200, blank=True)
    english_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for English term")
    spanish_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for Spanish term")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['english_term']
        verbose_name = "Immigration Term"
        verbose_name_plural = "Immigration Terms"

    def __str__(self):
        return self.english_term
class L2Term(models.Model):
    english_term               = models.CharField(max_length=200, unique=True)
    spanish_term               = models.CharField(max_length=200, blank=True)
    english_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for English term")
    spanish_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for Spanish term")
    created_at                 = models.DateTimeField(auto_now_add=True)
    updated_at                 = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['english_term']
        verbose_name = "L2 Term"
        verbose_name_plural = "L2 Terms"

    def __str__(self):
        return self.english_term


class L3Term(models.Model):
    english_term               = models.CharField(max_length=200, unique=True)
    spanish_term               = models.CharField(max_length=200, blank=True)
    english_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for English term")
    spanish_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for Spanish term")
    created_at                 = models.DateTimeField(auto_now_add=True)
    updated_at                 = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['english_term']
        verbose_name = "L3 Term"
        verbose_name_plural = "L3 Terms"

    def __str__(self):
        return self.english_term
    
class MedicareGlossaryTerm(models.Model):
    english_term = models.CharField(max_length=255, unique=True)
    spanish_term = models.CharField(max_length=255, blank=True, null=True)
    english_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for English term")
    spanish_phonetic = models.CharField(max_length=500, blank=True, null=True, help_text="IPA phonetic spelling for Spanish term")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['english_term']
        verbose_name = "Medicare Glossary Term"
        verbose_name_plural = "Medicare Glossary Terms"

    def __str__(self):
        return self.english_term

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    title_es = models.CharField(max_length=200, blank=True, null=True)
    author = models.CharField(max_length=100, default="InterpAscend Team")
    slug = models.SlugField(unique=True)
    content = models.TextField()
    content_es = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)
    featured_image = models.ImageField(upload_to='blog/', blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"

    def __str__(self):
        return self.title

class Feedback(models.Model):
    FEEDBACK_TYPES = [
        ('suggestion', 'General Suggestion'),
        ('bug', 'Bug Report'),
        ('term', 'Term Suggestion'),
        ('general', 'General Feedback'),
    ]
    
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    email = models.EmailField(blank=True, null=True, help_text="Optional - for follow-up responses")
    term_reference = models.CharField(max_length=200, blank=True, null=True, help_text="If suggesting a term, enter it here")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New'),
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved'),
            ('closed', 'Closed'),
        ],
        default='new'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Feedback"
        verbose_name_plural = "Feedback"

    def __str__(self):
        return f"{self.get_feedback_type_display()} - {self.subject}"


class TermHelpfulness(models.Model):
    """
    Model to store user feedback on term helpfulness.
    Tracks whether users find specific terms helpful or not.
    """
    TERM_TYPES = [
        ('medication', 'Medication'),
        ('diagnosis', 'Diagnosis'),
        ('mesh', 'MeSH Term'),
        ('financial', 'Financial Term'),
        ('agency', 'Government Agency'),
        ('immigration', 'Immigration Term'),
        ('l2', 'L2 Term'),
        ('l3', 'L3 Term'),
        ('medicare', 'Medicare Term'),
        ('llm', 'LLM Generated'),
    ]
    
    # Core feedback data
    is_helpful = models.BooleanField(
        help_text="True if helpful, False if not helpful"
    )
    term_reference = models.CharField(
        max_length=500,
        help_text="The term that was rated"
    )
    term_type = models.CharField(
        max_length=20,
        choices=TERM_TYPES,
        help_text="Category of the term being rated"
    )
    term_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Database ID of the term (null for LLM terms)"
    )
    
    # User context (anonymous)
    session_id = models.CharField(
        max_length=100,
        help_text="Anonymous user session identifier"
    )
    user_comment = models.TextField(
        blank=True,
        null=True,
        help_text="Optional user feedback comment"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Term Helpfulness Feedback"
        verbose_name_plural = "Term Helpfulness Feedback"
        # Prevent duplicate feedback from same session for same term
        unique_together = ['session_id', 'term_reference', 'term_type']
        indexes = [
            models.Index(fields=['term_type', 'created_at']),
            models.Index(fields=['is_helpful', 'term_type']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        helpful_text = "👍 Helpful" if self.is_helpful else "👎 Not Helpful"
        return f"{self.term_reference} ({self.term_type}) - {helpful_text}"
    
    @property
    def has_comment(self):
        """Returns True if user provided a comment"""
        return bool(self.user_comment and self.user_comment.strip())
