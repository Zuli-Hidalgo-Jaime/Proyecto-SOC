/**
 * Global configuration for the frontend
 * – Ajusta API_BASE_URL si cambias de host/puerto
 */
const CONFIG = {
    API_BASE_URL: "http://localhost:8000",
  
    ENDPOINTS: {
      TICKETS      : "/api/tickets/",                    // barra final
      TICKET_BY_ID : id => `/api/tickets/${id}`,
      CREATE_TICKET: "/api/tickets/",
      UPDATE_TICKET: id => `/api/tickets/${id}`,
      DELETE_TICKET: id => `/api/tickets/${id}`
    },
  
    STATUS_OPTIONS: { ABIERTO: "Nuevo", EN_PROCESO: "En proceso", CERRADO: "Cerrado" },
  
    UI: {
      SEARCH_DELAY          : 400,
      AUTO_REFRESH_INTERVAL : 30_000   // 30 s
    }
  };
  
  // Export para tests Node
  if (typeof module !== "undefined" && module.exports) module.exports = CONFIG;
  