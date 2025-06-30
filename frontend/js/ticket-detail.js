/**
 * Ticket detail functionality
 * Handles loading and displaying individual ticket details
 */

class TicketDetailManager {
    constructor() {
        this.ticketId = this.getTicketIdFromUrl();
        this.ticket = null;
        this.init();
    }

    init() {
        if (this.ticketId) {
            this.loadTicket();
            this.setupEventListeners();
        } else {
            this.showError(true);
        }
    }

    getTicketIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('id');
    }

    async loadTicket() {
        try {
            this.showLoading(true);
            const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.TICKET_BY_ID(this.ticketId)}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.ticket = await response.json();
            this.renderTicket();
            this.showLoading(false);
        } catch (error) {
            console.error('Error loading ticket:', error);
            this.showError(true);
            this.showLoading(false);
        }
    }

    renderTicket() {
        if (!this.ticket) return;

        // Update page title
        document.title = `Ticket #${this.ticket.id} - ${this.ticket.title} - ProyectoSoc`;

        // Fill ticket information
        document.getElementById('ticketId').textContent = this.ticket.id;
        document.getElementById('ticketTitle').textContent = this.ticket.title;
        document.getElementById('ticketDescription').textContent = this.ticket.description;
        document.getElementById('ticketPriority').textContent = this.getPriorityDisplayName(this.ticket.priority);
        document.getElementById('ticketCategory').textContent = this.getCategoryDisplayName(this.ticket.category);
        document.getElementById('ticketCreated').textContent = this.formatDate(this.ticket.created_at);
        document.getElementById('ticketUpdated').textContent = this.formatDate(this.ticket.updated_at);

        // Update status badge
        const statusElement = document.getElementById('ticketStatus');
        statusElement.textContent = this.getStatusDisplayName(this.ticket.status);
        statusElement.className = `status-badge status-${this.ticket.status}`;

        // Show ticket detail section
        document.getElementById('ticketDetail').classList.remove('hidden');
    }

    setupEventListeners() {
        // Edit button
        const editBtn = document.getElementById('editTicket');
        if (editBtn) {
            editBtn.addEventListener('click', () => {
                // TODO: Implement edit functionality
                alert('Funcionalidad de edición en desarrollo');
            });
        }

        // Change status button
        const changeStatusBtn = document.getElementById('changeStatus');
        if (changeStatusBtn) {
            changeStatusBtn.addEventListener('click', () => {
                this.showStatusChangeDialog();
            });
        }

        // Delete button
        const deleteBtn = document.getElementById('deleteTicket');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                this.confirmDelete();
            });
        }
    }

    showStatusChangeDialog() {
        const newStatus = prompt(
            'Selecciona el nuevo estado:\n1. Abierto\n2. En Proceso\n3. Cerrado',
            '1'
        );

        if (newStatus) {
            const statusMap = {
                '1': CONFIG.STATUS_OPTIONS.ABIERTO,
                '2': CONFIG.STATUS_OPTIONS.EN_PROCESO,
                '3': CONFIG.STATUS_OPTIONS.CERRADO
            };

            const selectedStatus = statusMap[newStatus];
            if (selectedStatus) {
                this.updateTicketStatus(selectedStatus);
            }
        }
    }

    async updateTicketStatus(newStatus) {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.UPDATE_TICKET(this.ticketId)}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...this.ticket,
                    status: newStatus
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Reload ticket to show updated status
            this.loadTicket();
        } catch (error) {
            console.error('Error updating ticket status:', error);
            alert('Error al actualizar el estado del ticket');
        }
    }

    confirmDelete() {
        const confirmed = confirm('¿Estás seguro de que quieres eliminar este ticket? Esta acción no se puede deshacer.');
        
        if (confirmed) {
            this.deleteTicket();
        }
    }

    async deleteTicket() {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.DELETE_TICKET(this.ticketId)}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            alert('Ticket eliminado exitosamente');
            window.location.href = 'index.html';
        } catch (error) {
            console.error('Error deleting ticket:', error);
            alert('Error al eliminar el ticket');
        }
    }

    showLoading(show) {
        const loading = document.getElementById('loading');
        const error = document.getElementById('error');
        
        if (loading) loading.classList.toggle('hidden', !show);
        if (error) error.classList.toggle('hidden', true);
    }

    showError(show) {
        const error = document.getElementById('error');
        if (error) error.classList.toggle('hidden', !show);
    }

    getStatusDisplayName(status) {
        const statusNames = {
            'abierto': 'Abierto',
            'en_proceso': 'En Proceso',
            'cerrado': 'Cerrado'
        };
        return statusNames[status] || status;
    }

    getPriorityDisplayName(priority) {
        const priorityNames = {
            'baja': 'Baja',
            'media': 'Media',
            'alta': 'Alta',
            'crítica': 'Crítica'
        };
        return priorityNames[priority] || priority;
    }

    getCategoryDisplayName(category) {
        const categoryNames = {
            'soporte': 'Soporte Técnico',
            'bug': 'Bug/Error',
            'feature': 'Nueva Funcionalidad',
            'consulta': 'Consulta'
        };
        return categoryNames[category] || category;
    }

    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TicketDetailManager();
}); 