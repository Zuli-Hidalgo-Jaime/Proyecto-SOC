/**
 * Main tickets list functionality
 * Handles loading, filtering and displaying tickets
 */

class TicketsManager {
    constructor() {
        this.tickets = [];
        this.filteredTickets = [];
        this.init();
    }

    init() {
        this.loadTickets();
        this.setupEventListeners();
        this.setupAutoRefresh();
    }

    async loadTickets() {
        try {
            this.showLoading(true);
            const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.TICKETS}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.tickets = await response.json();
            this.filteredTickets = [...this.tickets];
            this.renderTickets();
            this.showLoading(false);
        } catch (error) {
            console.error('Error loading tickets:', error);
            this.showError(true);
            this.showLoading(false);
        }
    }

    renderTickets() {
        const tbody = document.getElementById('ticketsTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (this.filteredTickets.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; padding: 2rem;">
                        No se encontraron tickets
                    </td>
                </tr>
            `;
            return;
        }

        this.filteredTickets.forEach(ticket => {
            const row = this.createTicketRow(ticket);
            tbody.appendChild(row);
        });
    }

    createTicketRow(ticket) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${ticket.id}</td>
            <td>
                <a href="ticket-detail.html?id=${ticket.id}" class="ticket-title">
                    ${this.escapeHtml(ticket.title)}
                </a>
            </td>
            <td>
                <span class="status-badge status-${ticket.status}">
                    ${this.getStatusDisplayName(ticket.status)}
                </span>
            </td>
            <td>${this.formatDate(ticket.created_at)}</td>
            <td>
                <a href="ticket-detail.html?id=${ticket.id}" class="btn btn-secondary" style="padding: 0.25rem 0.5rem; font-size: 0.8rem;">
                    Ver
                </a>
            </td>
        `;
        return row;
    }

    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.filterTickets();
                }, CONFIG.UI.SEARCH_DELAY);
            });
        }

        // Status filter
        const statusFilter = document.getElementById('statusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', () => {
                this.filterTickets();
            });
        }
    }

    filterTickets() {
        const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
        const statusFilter = document.getElementById('statusFilter')?.value || '';

        this.filteredTickets = this.tickets.filter(ticket => {
            const matchesSearch = !searchTerm || 
                ticket.title.toLowerCase().includes(searchTerm) ||
                ticket.description.toLowerCase().includes(searchTerm);
            
            const matchesStatus = !statusFilter || ticket.status === statusFilter;

            return matchesSearch && matchesStatus;
        });

        this.renderTickets();
    }

    setupAutoRefresh() {
        setInterval(() => {
            this.loadTickets();
        }, CONFIG.UI.AUTO_REFRESH_INTERVAL);
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

    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TicketsManager();
}); 