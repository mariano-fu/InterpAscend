/**
 * Term Feedback Handler
 * Manages the term helpfulness feedback widget interactions
 */
class TermFeedbackHandler {
    constructor() {
        this.initializeEventListeners();
        this.initializeCharacterCounters();
    }
    
    initializeEventListeners() {
        document.addEventListener('click', (e) => {
            if (e.target.matches('.feedback-btn') || e.target.closest('.feedback-btn')) {
                this.handleFeedbackButtonClick(e);
            } else if (e.target.matches('.submit-feedback-btn') || e.target.closest('.submit-feedback-btn')) {
                this.handleSubmitFeedback(e);
            } else if (e.target.matches('.cancel-feedback-btn') || e.target.closest('.cancel-feedback-btn')) {
                this.handleCancelFeedback(e);
            }
        });
    }
    
    initializeCharacterCounters() {
        document.querySelectorAll('.feedback-comment').forEach(textarea => {
            textarea.addEventListener('input', (e) => {
                this.updateCharacterCount(e.target);
            });
        });
    }
    
    updateCharacterCount(textarea) {
        const widget = textarea.closest('.term-feedback-widget');
        const counter = widget.querySelector('.char-count');
        if (counter) {
            counter.textContent = textarea.value.length;
        }
    }
    
    handleFeedbackButtonClick(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const button = e.target.closest('.feedback-btn');
        const widget = button.closest('.term-feedback-widget');
        const isHelpful = button.dataset.helpful === 'true';
        
        // Store the feedback choice
        widget.dataset.isHelpful = isHelpful;
        
        // Update button states
        widget.querySelectorAll('.feedback-btn').forEach(btn => {
            btn.classList.remove('btn-success', 'btn-danger');
            btn.classList.add(btn.dataset.helpful === 'true' ? 'btn-outline-success' : 'btn-outline-danger');
        });
        
        // Highlight selected button
        button.classList.remove('btn-outline-success', 'btn-outline-danger');
        button.classList.add(isHelpful ? 'btn-success' : 'btn-danger');
        
        // Show comment section
        widget.querySelector('.feedback-question').style.display = 'none';
        widget.querySelector('.feedback-comment-section').style.display = 'block';
        
        // Focus on comment field if "No" was selected
        if (!isHelpful) {
            const commentField = widget.querySelector('.feedback-comment');
            commentField.focus();
            commentField.placeholder = "Please tell us what was wrong or missing so we can improve this term...";
        }
        
        // Track analytics
        this.trackAnalytics('feedback_option_selected', {
            term_type: widget.dataset.termType,
            is_helpful: isHelpful
        });
    }
    
    handleCancelFeedback(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const widget = e.target.closest('.term-feedback-widget');
        
        // Reset to initial state
        this.resetWidget(widget);
    }
    
    resetWidget(widget) {
        // Show question, hide other sections
        widget.querySelector('.feedback-question').style.display = 'block';
        widget.querySelector('.feedback-comment-section').style.display = 'none';
        widget.querySelector('.feedback-success').style.display = 'none';
        widget.querySelector('.feedback-error').style.display = 'none';
        widget.querySelector('.feedback-loading').style.display = 'none';
        
        // Reset button states
        widget.querySelectorAll('.feedback-btn').forEach(btn => {
            btn.classList.remove('btn-success', 'btn-danger');
            btn.classList.add(btn.dataset.helpful === 'true' ? 'btn-outline-success' : 'btn-outline-danger');
        });
        
        // Clear comment
        const commentField = widget.querySelector('.feedback-comment');
        commentField.value = '';
        this.updateCharacterCount(commentField);
        
        // Remove stored choice
        delete widget.dataset.isHelpful;
    }
    
    async handleSubmitFeedback(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const widget = e.target.closest('.term-feedback-widget');
        const submitBtn = widget.querySelector('.submit-feedback-btn');
        
        // Show loading state
        this.showLoading(widget);
        
        try {
            const response = await fetch('/terminology/feedback/submit/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    is_helpful: widget.dataset.isHelpful === 'true',
                    term_reference: widget.dataset.termReference,
                    term_type: widget.dataset.termType,
                    term_id: widget.dataset.termId || null,
                    user_comment: widget.querySelector('.feedback-comment').value.trim()
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccess(widget, data.message);
                
                // Track successful submission
                this.trackAnalytics('term_feedback_submitted', {
                    term_type: widget.dataset.termType,
                    is_helpful: widget.dataset.isHelpful === 'true',
                    has_comment: widget.querySelector('.feedback-comment').value.trim().length > 0
                });
            } else {
                this.showError(widget, data.message);
            }
        } catch (error) {
            console.error('Feedback submission error:', error);
            this.showError(widget, 'Network error. Please check your connection and try again.');
        }
    }
    
    showLoading(widget) {
        widget.querySelector('.feedback-comment-section').style.display = 'none';
        widget.querySelector('.feedback-loading').style.display = 'block';
        widget.querySelector('.feedback-error').style.display = 'none';
    }
    
    showSuccess(widget, message) {
        widget.querySelector('.feedback-loading').style.display = 'none';
        widget.querySelector('.feedback-success').style.display = 'block';
        
        // Update success message if provided
        if (message) {
            const successAlert = widget.querySelector('.feedback-success .alert');
            const icon = successAlert.querySelector('i');
            const strong = successAlert.querySelector('strong');
            successAlert.innerHTML = '';
            successAlert.appendChild(icon);
            successAlert.appendChild(strong);
            successAlert.appendChild(document.createTextNode(' ' + message));
        }
    }
    
    showError(widget, message) {
        widget.querySelector('.feedback-loading').style.display = 'none';
        widget.querySelector('.feedback-comment-section').style.display = 'block';
        widget.querySelector('.feedback-error').style.display = 'block';
        widget.querySelector('.error-message').textContent = message;
        
        // Re-enable submit button
        const submitBtn = widget.querySelector('.submit-feedback-btn');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane me-1"></i> Submit Feedback';
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    trackAnalytics(eventName, parameters) {
        // Google Analytics 4 tracking
        if (typeof gtag === 'function') {
            gtag('event', eventName, parameters);
        }
        
        // Console log for debugging
        console.log('Analytics Event:', eventName, parameters);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TermFeedbackHandler();
});

// Export for potential use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TermFeedbackHandler;
}