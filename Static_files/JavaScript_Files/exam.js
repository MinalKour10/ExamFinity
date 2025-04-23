/**
 * exam.js - Handles exam-related functionality
 */

// Timer variables
let examDuration = 0; // in seconds
let timerInterval = null;
let endTime = null;

// Initialize exam timer
function initExamTimer(durationMinutes) {
    examDuration = durationMinutes * 60; // convert to seconds
    endTime = new Date(Date.now() + examDuration * 1000);
    
    // Update timer display immediately
    updateTimerDisplay();
    
    // Set up timer interval
    timerInterval = setInterval(updateTimerDisplay, 1000);
    
    console.log(`Exam timer initialized for ${durationMinutes} minutes`);
}

// Update timer display
function updateTimerDisplay() {
    const timerElement = document.getElementById('exam-timer');
    if (!timerElement) return;
    
    const now = new Date();
    const timeLeft = Math.max(0, Math.floor((endTime - now) / 1000));
    
    if (timeLeft <= 0) {
        clearInterval(timerInterval);
        timerElement.innerHTML = '<span class="text-danger">Time Expired</span>';
        
        // Auto-submit form
        autoSubmitExam();
        return;
    }
    
    // Format time remaining
    const hours = Math.floor(timeLeft / 3600);
    const minutes = Math.floor((timeLeft % 3600) / 60);
    const seconds = timeLeft % 60;
    
    // Display time with appropriate colors
    let timerClass = 'text-success';
    if (timeLeft < 300) { // less than 5 minutes
        timerClass = 'text-danger';
    } else if (timeLeft < 600) { // less than 10 minutes
        timerClass = 'text-warning';
    }
    
    timerElement.innerHTML = `<span class="${timerClass}">Time Remaining: ${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}</span>`;
}

// Auto-submit exam when time expires
function autoSubmitExam() {
    const examForm = document.getElementById('exam-form');
    if (examForm) {
        // Create a submission indicator
        const submissionNote = document.createElement('div');
        submissionNote.className = 'alert alert-danger mt-3';
        submissionNote.innerHTML = 'Time expired! Your exam is being submitted...';
        document.querySelector('.container').appendChild(submissionNote);
        
        // Mark that we're submitting to prevent tab switch warnings
        window.isSubmitting = true;
        
        // Submit the form
        setTimeout(() => {
            examForm.submit();
        }, 2000);
    }
}

// Save answers periodically to prevent data loss
function setupAutosave() {
    const examForm = document.getElementById('exam-form');
    if (!examForm) return;
    
    // Save every 30 seconds
    setInterval(() => {
        const formData = new FormData(examForm);
        
        // Add autosave flag
        formData.append('autosave', 'true');
        
        // Use fetch to send data to server
        fetch(examForm.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Answers autosaved:', data);
            
            // Show a temporary message
            const saveIndicator = document.getElementById('autosave-indicator');
            if (saveIndicator) {
                saveIndicator.textContent = 'Answers saved at ' + new Date().toLocaleTimeString();
                saveIndicator.style.opacity = '1';
                
                // Fade out the message
                setTimeout(() => {
                    saveIndicator.style.opacity = '0';
                }, 3000);
            }
        })
        .catch(error => {
            console.error('Error autosaving answers:', error);
        });
    }, 30000); // 30 seconds
}

// Question navigation
function setupQuestionNavigation() {
    const questionNav = document.getElementById('question-nav');
    const questionContainers = document.querySelectorAll('.question-container');
    
    if (!questionNav || questionContainers.length === 0) return;
    
    // Create navigation buttons
    questionContainers.forEach((container, index) => {
        const button = document.createElement('button');
        button.className = 'btn btn-outline-primary m-1 question-nav-btn';
        button.setAttribute('data-question', index + 1);
        button.textContent = index + 1;
        
        button.addEventListener('click', () => {
            // Hide all questions
            questionContainers.forEach(q => q.classList.add('d-none'));
            
            // Show selected question
            questionContainers[index].classList.remove('d-none');
            
            // Update active state
            document.querySelectorAll('.question-nav-btn').forEach(btn => {
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-outline-primary');
            });
            button.classList.remove('btn-outline-primary');
            button.classList.add('btn-primary');
        });
        
        questionNav.appendChild(button);
    });
    
    // Initialize with first question
    if (questionContainers.length > 0) {
        questionContainers.forEach((q, i) => {
            if (i > 0) q.classList.add('d-none');
        });
        
        const firstButton = document.querySelector('.question-nav-btn');
        if (firstButton) {
            firstButton.classList.remove('btn-outline-primary');
            firstButton.classList.add('btn-primary');
        }
    }
}

// Mark questions as answered in the navigation
function updateQuestionNavigation() {
    const inputs = document.querySelectorAll('input[type="radio"]:checked, textarea');
    
    inputs.forEach(input => {
        const questionId = input.closest('.question-container')?.getAttribute('data-question-id');
        if (questionId) {
            const navButton = document.querySelector(`.question-nav-btn[data-question="${questionId}"]`);
            if (navButton && input.value.trim() !== '') {
                navButton.classList.add('btn-success');
                navButton.classList.remove('btn-outline-primary', 'btn-primary');
            }
        }
    });
}

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on an exam page
    const examTimerElement = document.getElementById('exam-timer');
    if (examTimerElement) {
        const durationMinutes = parseInt(examTimerElement.getAttribute('data-duration') || '0');
        if (durationMinutes > 0) {
            initExamTimer(durationMinutes);
        }
    }
    
    // Setup question navigation if needed
    setupQuestionNavigation();
    
    // Setup autosave functionality
    setupAutosave();
    
    // Add event listeners to update navigation when answers change
    document.querySelectorAll('input[type="radio"], textarea').forEach(input => {
        input.addEventListener('change', updateQuestionNavigation);
    });
});
