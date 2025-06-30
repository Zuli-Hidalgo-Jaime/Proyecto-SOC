/**
 * Configuration file for the frontend application
 * Contains API endpoints and global settings
 */

const CONFIG = {
    // API base URL - change this for production
    API_BASE_URL: 'http://localhost:8000',
    
    // API endpoints
    ENDPOINTS: {
        TICKETS: '/api/tickets',
        TICKET_BY_ID: (id) => `/api/tickets/${id}`,
        CREATE_TICKET: '/api/tickets',
        UPDATE_TICKET: (id) => `/api/tickets/${id}`,
        DELETE_TICKET: (id) => `/api/tickets/${id}`,
    },
    
    // Ticket status options
    STATUS_OPTIONS: {
        ABIERTO: 'abierto',
        EN_PROCESO: 'en_proceso',
        CERRADO: 'cerrado'
    },
    
    // Priority options
    PRIORITY_OPTIONS: {
        BAJA: 'baja',
        MEDIA: 'media',
        ALTA: 'alta',
        CRITICA: 'crítica'
    },
    
    // Category options
    CATEGORY_OPTIONS: {
        SOPORTE: 'soporte',
        BUG: 'bug',
        FEATURE: 'feature',
        CONSULTA: 'consulta'
    },
    
    // UI settings
    UI: {
        ITEMS_PER_PAGE: 20,
        SEARCH_DELAY: 300, // milliseconds
        AUTO_REFRESH_INTERVAL: 30000 // 30 seconds
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
} 