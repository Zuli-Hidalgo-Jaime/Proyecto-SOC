/**
 * Ticket detail – maneja la carga, visualización, cambio de estado y borrado
 * Requiere los siguientes IDs en el HTML:
 *  'ticketDetail', 'loading', 'error',
 *  'ticketId', 'ticketTitle', 'ticketDescription',
 *  'ticketPriority', 'ticketCategory',
 *  'ticketCreated', 'ticketUpdated', 'ticketStatus',
 *  y botones opcionales con IDs: 'editTicket', 'changeStatus', 'deleteTicket'
 */

class TicketDetailManager {
    constructor() {
      this.ticketId = new URLSearchParams(window.location.search).get("id");
      if (this.ticketId) {
        this.loadTicket();
        this.bindEvents();
      } else {
        this.show("error", true);
      }
    }
  
    /* ────────────────────────────────────────────── */
    /* 1. Cargar ticket                              */
    /* ────────────────────────────────────────────── */
    async loadTicket() {
      try {
        this.show("loading", true);
        const res = await fetch(
          `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.TICKET_BY_ID(this.ticketId)}`
        );
        if (!res.ok) throw new Error(await res.text());
        this.ticket = await res.json();
        this.render();
      } catch (err) {
        console.error("Error loading ticket:", err);
        this.show("error", true);
      } finally {
        this.show("loading", false);
      }
    }
  
    /* ────────────────────────────────────────────── */
    /* 2. Renderizar datos                           */
    /* ────────────────────────────────────────────── */
    render() {
      if (!this.ticket) return;
      const t = this.ticket;
  
      document.title = `Ticket ${t.TicketNumber} – ProyectoSoc`;
  
      document.getElementById("ticketId").textContent          = t.TicketNumber;
      document.getElementById("ticketTitle").textContent       = t.ShortDescription;
      document.getElementById("ticketDescription").textContent = t.Description || "";
      document.getElementById("ticketPriority").textContent    = t.Priority    || "";
      document.getElementById("ticketCategory").textContent    = t.Category    || "";
      document.getElementById("ticketCreated").textContent     = this.f(t.CreatedAt);
      document.getElementById("ticketUpdated").textContent     = this.f(t.UpdatedAt);
  
      const badge = document.getElementById("ticketStatus");
      badge.textContent = t.Status;
      badge.className   = `status-badge status-${t.Status.toLowerCase()}`;
  
      this.show("ticketDetail", true);
    }
  
    /* ────────────────────────────────────────────── */
    /* 3. Eventos (editar, cambiar estado, borrar)   */
    /* ────────────────────────────────────────────── */
    bindEvents() {
      document.getElementById("editTicket")?.addEventListener("click", () => this.showEditModal());
      document.getElementById("changeStatus")?.addEventListener("click", () => this.showStatusDialog());
      document.getElementById("deleteTicket")?.addEventListener("click", () => this.confirmDelete());
    
      // Edit Modal events
      document.getElementById("closeEditModal")?.addEventListener("click", () => this.hideEditModal());
      document.getElementById("cancelEdit")?.addEventListener("click", () => this.hideEditModal());
      document.getElementById("editTicketForm")?.addEventListener("submit", (e) => {
        e.preventDefault();
        this.submitEdit();
      });
    }
    
    showEditModal() {
      // Llena los campos del modal con los valores actuales
      document.getElementById("editTitle").value        = this.ticket.ShortDescription || '';
      document.getElementById("editDescription").value  = this.ticket.Description || '';
      document.getElementById("editPriority").value     = this.ticket.Priority || '';
      document.getElementById("editCategory").value     = this.ticket.Category || '';
      document.getElementById("editAssignedTo").value   = this.ticket.AssignedTo || '';
      document.getElementById("editModal").classList.remove("hidden");
    }
    
    hideEditModal() {
      document.getElementById("editModal").classList.add("hidden");
    }
    
    async submitEdit() {
      // Construye los campos editables + los requeridos en PascalCase
      const body = {
        TicketNumber    : this.ticket.TicketNumber,
        Folio           : this.ticket.Folio,
        ShortDescription: document.getElementById("editTitle").value,
        Description     : document.getElementById("editDescription").value,
        CreatedBy       : this.ticket.CreatedBy,              // << OBLIGATORIO
        Company         : this.ticket.Company,
        ReportedBy      : this.ticket.ReportedBy,
        Category        : document.getElementById("editCategory").value,
        Subcategory     : this.ticket.Subcategory,
        Severity        : this.ticket.Severity,
        Impact          : this.ticket.Impact,
        Urgency         : this.ticket.Urgency,
        Priority        : document.getElementById("editPriority").value,
        Status          : this.ticket.Status, // No cambias status aquí
        Workflow        : this.ticket.Workflow,
        Channel         : this.ticket.Channel,
        AssignmentGroup : this.ticket.AssignmentGroup,
        AssignedTo      : document.getElementById("editAssignedTo").value,
      };
    
      try {
        const res = await fetch(
          `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.UPDATE_TICKET(this.ticketId)}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
          }
        );
        if (!res.ok) throw new Error(await res.text());
        this.hideEditModal();
        this.loadTicket(); // Refresca la vista
        alert("Ticket actualizado exitosamente.");
      } catch (err) {
        console.error("Error al editar ticket:", err);
        alert("Error al editar el ticket.");
      }
    }
  
    /* ---- Cambiar estado ------------------------- */
    showStatusDialog() {
      const opt = prompt("Nuevo estado:\n1. Nuevo\n2. En proceso\n3. Cerrado", "1");
      const map = { "1": "Nuevo", "2": "En proceso", "3": "Cerrado" };
      const status = map[opt];
      if (status) this.updateTicketStatus(status);
    }
  
    async updateTicketStatus(newStatus) {
      try {
        // El ticket que tienes probablemente tiene claves minúsculas
        // Pero el backend espera PascalCase (exactamente igual al GET)
        const t = this.ticket;
        const body = {
          TicketNumber:    t.TicketNumber,
          Folio:           t.Folio,
          ShortDescription:t.ShortDescription,
          Description:     t.Description,
          CreatedBy:       t.CreatedBy,
          Company:         t.Company,
          ReportedBy:      t.ReportedBy,
          Category:        t.Category,
          Subcategory:     t.Subcategory,
          Severity:        t.Severity,
          Impact:          t.Impact,
          Urgency:         t.Urgency,
          Priority:        t.Priority,
          Status:          newStatus,                
          Workflow:        t.Workflow,
          Channel:         t.Channel,
          AssignmentGroup: t.AssignmentGroup,
          AssignedTo:      t.AssignedTo,
          // No envíes created_at, updated_at, id
        };
    
        const response = await fetch(
          `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.UPDATE_TICKET(this.ticketId)}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
          }
        );
    
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
    
        this.loadTicket();
      } catch (error) {
        console.error('Error updating ticket status:', error);
        alert('Error al actualizar el estado del ticket');
      }
    }
  
    /* ---- Eliminar ticket ------------------------ */
    confirmDelete() {
      if (confirm("¿Eliminar este ticket?")) this.deleteTicket();
    }
  
    async deleteTicket() {
      try {
        const res = await fetch(
          `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.DELETE_TICKET(this.ticketId)}`,
          { method: "DELETE" }
        );
        if (!res.ok) throw new Error(await res.text());
        alert("Ticket eliminado");
        location.href = "index.html";
      } catch (e) {
        console.error("Error deleting ticket:", e);
        alert("Error al eliminar el ticket");
      }
    }
  
    /* ────────────────────────────────────────────── */
    /* 4. Utils                                      */
    /* ────────────────────────────────────────────── */
    show(id, v) { document.getElementById(id)?.classList.toggle("hidden", !v); }
    f(d) { return d ? new Date(d).toLocaleString("es-MX") : ""; }
  }
  
  /* init */
  document.addEventListener("DOMContentLoaded", () => new TicketDetailManager());
  