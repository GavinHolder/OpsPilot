// Calendar App JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeCalendar();
});

function initializeCalendar() {
    // Initialize event handlers
    initializeEventHandlers();
    initializeQuickEventForm();
    initializeRSVPButtons();
    initializeDatePickers();
    initializeTooltips();
}

function initializeEventHandlers() {
    // Calendar navigation
    const calendarNavButtons = document.querySelectorAll('.calendar-nav-btn');
    calendarNavButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('href');
            loadCalendarView(url);
        });
    });

    // Event clicks
    const eventElements = document.querySelectorAll('.calendar-event, .week-event, .day-event');
    eventElements.forEach(element => {
        element.addEventListener('click', function(e) {
            e.preventDefault();
            const eventId = this.dataset.eventId;
            if (eventId) {
                window.location.href = `/calendar/event/${eventId}/`;
            }
        });
    });

    // Calendar day clicks (for creating events)
    const calendarDays = document.querySelectorAll('.calendar-day');
    calendarDays.forEach(day => {
        day.addEventListener('dblclick', function() {
            const date = this.dataset.date;
            if (date) {
                window.location.href = `/calendar/event/create/?start_date=${date}`;
            }
        });
    });
}

function initializeQuickEventForm() {
    const quickForm = document.getElementById('quick-event-form');
    if (!quickForm) return;

    quickForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(this);
        const submitButton = this.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;

        // Show loading state
        submitButton.innerHTML = '<span class="spinner"></span> Creating...';
        submitButton.disabled = true;

        fetch(this.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Event created successfully!', 'success');
                    this.reset();
                    // Optionally reload calendar or redirect
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showNotification(data.error || 'Error creating event', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error creating event', 'error');
            })
            .finally(() => {
                // Restore button state
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            });
    });
}

function initializeRSVPButtons() {
    const rsvpButtons = document.querySelectorAll('.rsvp-btn');

    rsvpButtons.forEach(button => {
        button.addEventListener('click', function() {
            const eventId = this.dataset.eventId;
            const status = this.dataset.status;

            if (!eventId || !status) return;

            const originalText = this.innerHTML;
            this.innerHTML = '<span class="spinner"></span>';
            this.disabled = true;

            fetch(`/calendar/event/${eventId}/rsvp/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: `status=${status}`
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification(data.message, 'success');

                        // Update UI to reflect new status
                        updateRSVPStatus(eventId, status);

                        // Remove invitation card if on dashboard
                        const invitationCard = this.closest('.col-md-6');
                        if (invitationCard && invitationCard.closest('[data-invitation-list]')) {
                            invitationCard.remove();
                        }
                    } else {
                        showNotification(data.error || 'Error updating RSVP', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('Error updating RSVP', 'error');
                })
                .finally(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                });
        });
    });
}

function initializeDatePickers() {
    // Set minimum date to today for date inputs
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];

    dateInputs.forEach(input => {
        if (input.hasAttribute('data-allow-past')) return;
        input.setAttribute('min', today);
    });

    // Auto-adjust end time when start time changes
    const startTimeInput = document.querySelector('input[name="start_datetime"]');
    const endTimeInput = document.querySelector('input[name="end_datetime"]');

    if (startTimeInput && endTimeInput) {
        startTimeInput.addEventListener('change', function() {
            const startTime = new Date(this.value);
            if (startTime && (!endTimeInput.value || new Date(endTimeInput.value) <= startTime)) {
                const endTime = new Date(startTime.getTime() + 60 * 60 * 1000); // Add 1 hour
                endTimeInput.value = endTime.toISOString().slice(0, 16);
            }
        });
    }
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips if available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

function loadCalendarView(url) {
    const calendarContainer = document.querySelector('.calendar-container');
    if (!calendarContainer) return;

    // Show loading state
    calendarContainer.classList.add('loading');

    fetch(url)
        .then(response => response.text())
        .then(html => {
            // Parse the HTML and extract the calendar content
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newContent = doc.querySelector('.calendar-container');

            if (newContent) {
                calendarContainer.innerHTML = newContent.innerHTML;
                initializeEventHandlers(); // Re-initialize event handlers
            }
        })
        .catch(error => {
            console.error('Error loading calendar view:', error);
            showNotification('Error loading calendar', 'error');
        })
        .finally(() => {
            calendarContainer.classList.remove('loading');
        });
}

function updateRSVPStatus(eventId, status) {
    // Update any RSVP status displays on the page
    const statusElements = document.querySelectorAll(`[data-event-id="${eventId}"] .rsvp-status`);

    statusElements.forEach(element => {
        element.className = `badge rsvp-status badge-status-${status.toLowerCase()}`;
        element.textContent = status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
    });
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';

    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Add to page
    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);

    // Add click to dismiss
    const closeButton = notification.querySelector('.btn-close');
    if (closeButton) {
        closeButton.addEventListener('click', () => {
            notification.remove();
        });
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Calendar utility functions
function formatEventTime(startTime, endTime) {
    const start = new Date(startTime);
    const end = new Date(endTime);

    const formatTime = (date) => {
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    };

    return `${formatTime(start)} - ${formatTime(end)}`;
}

function getEventPosition(startTime, duration) {
    const start = new Date(startTime);
    const startHour = start.getHours();
    const startMinute = start.getMinutes();

    const topPercent = ((startHour * 60 + startMinute) / (24 * 60)) * 100;
    const heightPercent = (duration / (24 * 60)) * 100;

    return {
        top: `${topPercent}%`,
        height: `${Math.max(heightPercent, 2)}%` // Minimum 2% height
    };
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

// Export functions for use in other scripts
window.CalendarApp = {
    initializeCalendar,
    loadCalendarView,
    showNotification,
    formatEventTime,
    getEventPosition,
    truncateText
};