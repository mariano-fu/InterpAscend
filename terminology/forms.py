from django import forms
from .models import Feedback, TermHelpfulness

class MedicationSearchForm(forms.Form):
    query = forms.CharField(
        label="Medication Name",
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Search medication…'})
    )

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['feedback_type', 'subject', 'message', 'email', 'term_reference']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'term_reference': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control dark:bg-gray-700 dark:text-gray-100 dark:border-gray-600 rounded-lg'
            })


class TermHelpfulnessForm(forms.ModelForm):
    """Form for handling term helpfulness feedback submissions"""
    
    class Meta:
        model = TermHelpfulness
        fields = ['is_helpful', 'user_comment']
        widgets = {
            'user_comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional: Tell us how we can improve this term...',
                'class': 'form-control',
                'maxlength': 1000
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_comment'].required = False
        self.fields['user_comment'].label = 'How can we improve? (Optional)'
