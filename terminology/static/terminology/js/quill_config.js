// Wait for both DOM and Quill to be ready
function initializeQuillEditors() {
    console.log('Initializing Quill editors...');
    
    // Check if Quill is available
    if (typeof Quill === 'undefined') {
        console.error('Quill is not loaded');
        setTimeout(initializeQuillEditors, 100);
        return;
    }
    
    // Initialize content field
    const contentField = document.getElementById('id_content');
    if (contentField) {
        console.log('Found content field, initializing...');
        initializeQuillEditor('content', contentField);
    }
    
    // Initialize content_es field
    const contentEsField = document.getElementById('id_content_es');
    if (contentEsField) {
        console.log('Found content_es field, initializing...');
        initializeQuillEditor('content_es', contentEsField);
    }
}

function initializeQuillEditor(fieldName, textareaElement) {
    try {
        // Create container div
        const container = document.createElement('div');
        container.className = 'quill-container';
        container.style.marginBottom = '10px';
        
        // Create editor div
        const editorDiv = document.createElement('div');
        editorDiv.id = 'quill_' + fieldName;
        editorDiv.style.minHeight = '200px';
        editorDiv.style.backgroundColor = 'white';
        editorDiv.style.border = '1px solid #ccc';
        
        container.appendChild(editorDiv);
        
        // Insert container before textarea
        textareaElement.parentNode.insertBefore(container, textareaElement);
        
        // Hide original textarea
        textareaElement.style.display = 'none';
        
        // Initialize Quill with simplified toolbar
        const quill = new Quill('#quill_' + fieldName, {
            theme: 'snow',
            modules: {
                toolbar: [
                    [{ 'size': ['small', false, 'large', 'huge'] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ 'color': [] }, { 'background': [] }],
                    [{ 'header': [1, 2, 3, false] }],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    [{ 'align': [] }],
                    ['link'],
                    ['clean']
                ]
            },
            placeholder: 'Write your blog content here...'
        });
        
        console.log('Quill editor initialized for', fieldName);
        
        // Set initial content
        if (textareaElement.value.trim()) {
            quill.root.innerHTML = textareaElement.value;
        }
        
        // Update textarea on content change
        quill.on('text-change', function() {
            textareaElement.value = quill.root.innerHTML;
            console.log('Content updated for', fieldName);
        });
        
        // Ensure content is saved on form submit
        const form = textareaElement.closest('form');
        if (form) {
            form.addEventListener('submit', function() {
                textareaElement.value = quill.root.innerHTML;
                console.log('Form submitted, content saved for', fieldName);
            });
        }
        
        // Focus the editor to test interaction
        setTimeout(function() {
            quill.focus();
        }, 100);
        
    } catch (error) {
        console.error('Error initializing Quill editor:', error);
        // Show the original textarea if Quill fails
        textareaElement.style.display = 'block';
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeQuillEditors);
} else {
    initializeQuillEditors();
}

// Also try after a short delay in case of timing issues
setTimeout(initializeQuillEditors, 500);

// Simple CSS to ensure Quill works properly
const style = document.createElement('style');
style.textContent = `
    .ql-editor {
        min-height: 150px !important;
        font-size: 14px;
        line-height: 1.6;
        background: white !important;
        color: black !important;
    }
    
    .ql-toolbar {
        background: #f8f9fa !important;
        border: 1px solid #ccc !important;
    }
    
    .ql-container {
        border: 1px solid #ccc !important;
        border-top: none !important;
        font-family: inherit;
    }
    
    .quill-container {
        position: relative;
        z-index: 1;
    }
`;
document.head.appendChild(style);