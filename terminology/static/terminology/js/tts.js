/**
 * Text-to-Speech utility with proper language voice selection
 * Handles both English and Spanish pronunciation correctly
 */

class TTSManager {
    constructor() {
        this.voicesLoaded = false;
        this.availableVoices = [];
        this.currentUtterance = null;
        
        this.init();
    }
    
    init() {
        if ('speechSynthesis' in window) {
            this.loadVoices();
            speechSynthesis.onvoiceschanged = () => this.loadVoices();
        } else {
            console.warn('Speech synthesis not supported in this browser');
        }
    }
    
    loadVoices() {
        this.availableVoices = speechSynthesis.getVoices();
        this.voicesLoaded = this.availableVoices.length > 0;
        
        if (this.voicesLoaded) {
            console.log('TTS voices loaded:', this.availableVoices.length);
            // Log available Spanish voices for debugging
            const spanishVoices = this.availableVoices.filter(voice => 
                voice.lang.startsWith('es') || 
                voice.name.toLowerCase().includes('spanish') ||
                voice.name.toLowerCase().includes('español')
            );
            console.log('Available Spanish voices:', spanishVoices.map(v => `${v.name} (${v.lang})`));
        }
    }
    
    findBestVoice(language) {
        if (!this.voicesLoaded) {
            return null;
        }
        
        if (language === 'es') {
            // Look for Spanish voices with priority order
            const spanishVoice = this.availableVoices.find(voice => 
                voice.lang === 'es-ES' ||  // Spain Spanish (most common)
                voice.lang === 'es-MX' ||  // Mexican Spanish
                voice.lang === 'es-US' ||  // US Spanish
                voice.lang.startsWith('es-') ||
                voice.name.toLowerCase().includes('spanish') ||
                voice.name.toLowerCase().includes('español')
            );
            return spanishVoice;
        } else {
            // Look for English voices
            const englishVoice = this.availableVoices.find(voice => 
                voice.lang === 'en-US' ||
                voice.lang === 'en-GB' ||
                voice.lang.startsWith('en-') ||
                voice.name.toLowerCase().includes('english')
            );
            return englishVoice;
        }
    }
    
    speak(text, language = 'en', options = {}) {
        if (!('speechSynthesis' in window) || !text) {
            console.warn('Cannot speak: Speech synthesis not supported or no text provided');
            return false;
        }
        
        // Cancel any ongoing speech
        this.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Set language
        utterance.lang = language === 'es' ? 'es-ES' : 'en-US';
        
        // DEBUG: Log the request details
        console.log(`TTS Request - Text: "${text}", Language: "${language}", Target Lang: "${utterance.lang}"`);
        
        // Try to find the best voice
        const bestVoice = this.findBestVoice(language);
        if (bestVoice) {
            utterance.voice = bestVoice;
            console.log(`✓ Using ${language} voice:`, bestVoice.name, bestVoice.lang);
        } else {
            console.warn(`⚠️ No ${language} voice found, using default. Available voices:`,
                this.availableVoices.map(v => `${v.name} (${v.lang})`));
        }
        
        // Set speech parameters
        utterance.rate = options.rate || 0.8;
        utterance.pitch = options.pitch || 1.0;
        utterance.volume = options.volume || 1.0;
        
        // Set up event handlers
        if (options.onStart) utterance.onstart = options.onStart;
        if (options.onEnd) utterance.onend = options.onEnd;
        if (options.onError) utterance.onerror = options.onError;
        
        this.currentUtterance = utterance;
        speechSynthesis.speak(utterance);
        
        return true;
    }
    
    cancel() {
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
        }
        this.currentUtterance = null;
    }
    
    isSpeaking() {
        return 'speechSynthesis' in window && speechSynthesis.speaking;
    }
}

// Create global TTS manager instance
window.ttsManager = new TTSManager();

// Helper function for easy TTS button integration
window.handleTTSClick = function(event) {
    const button = event.target.closest('.tts-btn');
    if (!button) return;
    
    const text = button.dataset.text;
    const lang = button.dataset.lang || 'en';
    
    if (!text) {
        console.warn('No text provided for TTS');
        return;
    }
    
    // Visual feedback
    button.classList.add('speaking');
    button.style.opacity = '0.6';
    
    const success = window.ttsManager.speak(text, lang, {
        onEnd: function() {
            button.classList.remove('speaking');
            button.style.opacity = '';
        },
        onError: function(event) {
            console.error('TTS error:', event.error);
            button.classList.remove('speaking');
            button.style.opacity = '';
        }
    });
    
    if (!success) {
        button.classList.remove('speaking');
        button.style.opacity = '';
    }
};

// Auto-attach TTS click handlers to buttons with tts-btn class
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('tts-btn') || event.target.closest('.tts-btn')) {
        event.preventDefault();
        window.handleTTSClick(event);
    }
});

console.log('TTS Manager loaded and ready');