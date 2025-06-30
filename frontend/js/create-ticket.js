/**
 * Create ticket functionality
 * Handles form submission and ticket creation
 */

class CreateTicketManager {
    constructor() {
        this.form = document.getElementById('createTicketForm');
        this.init();
    }

    init() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        try {
            this.showLoading(true);
            this.hideMessages();

            const formData = new FormData(this.form);
            const ticketData = this.buildTicketData(formData);

            const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.CREATE_TICKET}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(ticketData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.showSuccess(true);
            this.form.reset();
            
            // Redirect to ticket detail after short delay
            setTimeout(() => {
                window.location.href = `ticket-detail.html?id=${result.id}`;
            }, 1500);

        } catch (error) {
            console.error('Error creating ticket:', error);
            this.showError(true);
        } finally {
            this.showLoading(false);
        }
    }

    buildTicketData(formData) {
        const ticketData = {
            title: formData.get('title'),
            description: formData.get('description'),
            priority: formData.get('priority'),
            category: formData.get('category'),
            status: CONFIG.STATUS_OPTIONS.ABIERTO // Default status
        };

        // Handle file attachments if needed
        const attachments = formData.getAll('attachments');
        if (attachments.length > 0 && attachments[0].size > 0) {
            ticketData.attachments = attachments;
        }

        return ticketData;
    }

    showLoading(show) {
        const loading = document.getElementById('loading');
        if (loading) loading.classList.toggle('hidden', !show);
    }

    showError(show) {
        const error = document.getElementById('error');
        if (error) error.classList.toggle('hidden', !show);
    }

    showSuccess(show) {
        const success = document.getElementById('success');
        if (success) success.classList.toggle('hidden', !show);
    }

    hideMessages() {
        this.showError(false);
        this.showSuccess(false);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CreateTicketManager();
}); 