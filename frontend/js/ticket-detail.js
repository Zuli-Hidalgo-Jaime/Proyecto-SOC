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

    document.getElementById("ticketId").textContent = t.TicketNumber;
    document.getElementById("ticketTitle").textContent = t.ShortDescription;
    document.getElementById("ticketDescription").textContent = t.Description || "";
    document.getElementById("ticketPriority").textContent = t.Priority || "";
    document.getElementById("ticketCategory").textContent = t.Category || "";
    document.getElementById("ticketCreated").textContent = this.f(t.CreatedAt);
    document.getElementById("ticketUpdated").textContent = this.f(t.UpdatedAt);

    const badge = document.getElementById("ticketStatus");
    badge.textContent = t.Status;
    badge.className = `status-badge status-${t.Status.toLowerCase()}`;

    // 🔥 Cargar adjuntos dinámicamente
    this.show("ticketDetail", true);
    this.loadAttachments();

    this.show("ticketDetail", true);
  }

  /* ---- Cargar archivos adjuntos desde el backend ---- */
  async loadAttachments() {
    const container = document.getElementById("attachments-list");
    container.innerHTML = ""; // Limpia
  
    try {
      const response = await fetch(
        `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.LIST_ATTACHMENTS(this.ticketId)}`
      );
      if (!response.ok) throw new Error(await response.text());
  
      const attachments = await response.json();
  
      if (attachments.length === 0) {
        container.innerHTML = "<p>No hay archivos adjuntos</p>";
      } else {
        const list = document.createElement("ul");
        list.classList.add("attachment-list");
  
        attachments.forEach(att => {
          const item = document.createElement("li");
          const link = document.createElement("a");
          link.href = att.url;
          link.target = "_blank";
          link.textContent = `📎 ${att.name}`;
        
          const deleteBtn = document.createElement("button");
          deleteBtn.textContent = "🗑️ Eliminar";
          deleteBtn.classList.add("btn", "btn-danger", "btn-sm");
          deleteBtn.style.marginLeft = "1rem";
          deleteBtn.addEventListener("click", () => this.deleteAttachment(att.id));
        
          item.appendChild(link);
          item.appendChild(deleteBtn);
          list.appendChild(item);
        });
  
        container.appendChild(list);
      }
    } catch (err) {
      console.error("Error cargando adjuntos:", err);
      container.innerHTML = "<p>Error al cargar los adjuntos</p>";
    }
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

    // Upload Attachment event
    document.getElementById("uploadAttachmentForm")?.addEventListener("submit", (e) => {
      e.preventDefault();
      this.uploadAttachment();
    });
  }

  showEditModal() {
    document.getElementById("editTitle").value = this.ticket.ShortDescription || '';
    document.getElementById("editDescription").value = this.ticket.Description || '';
    document.getElementById("editPriority").value = this.ticket.Priority || '';
    document.getElementById("editCategory").value = this.ticket.Category || '';
    document.getElementById("editAssignedTo").value = this.ticket.AssignedTo || '';
    document.getElementById("editModal").classList.remove("hidden");
  }

  hideEditModal() {
    document.getElementById("editModal").classList.add("hidden");
  }

  /* ---- Subir archivo adjunto ------------------------- */
  async uploadAttachment() {
    const input = document.getElementById("attachmentInput");
    if (!input.files.length) {
      alert("📎 Por favor selecciona un archivo.");
      return;
    }

    const formData = new FormData();
    formData.append("file", input.files[0]);

    try {
      const res = await fetch(
        `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.UPLOAD_ATTACHMENT(this.ticketId)}`,
        {
          method: "POST",
          body: formData
        }
      );
      if (!res.ok) throw new Error(await res.text());
      alert("✅ Archivo subido correctamente");
      this.loadTicket(); // Refrescar datos del ticket
    } catch (err) {
      console.error("Error al subir adjunto:", err);
      alert("❌ Error al subir el archivo");
    }
  }

  async submitEdit() {
    const body = {
      TicketNumber: this.ticket.TicketNumber,
      Folio: this.ticket.Folio,
      ShortDescription: document.getElementById("editTitle").value,
      Description: document.getElementById("editDescription").value,
      CreatedBy: this.ticket.CreatedBy,
      Company: this.ticket.Company,
      ReportedBy: this.ticket.ReportedBy,
      Category: document.getElementById("editCategory").value,
      Subcategory: this.ticket.Subcategory,
      Severity: this.ticket.Severity,
      Impact: this.ticket.Impact,
      Urgency: this.ticket.Urgency,
      Priority: document.getElementById("editPriority").value,
      Status: this.ticket.Status,
      Workflow: this.ticket.Workflow,
      Channel: this.ticket.Channel,
      AssignmentGroup: this.ticket.AssignmentGroup,
      AssignedTo: document.getElementById("editAssignedTo").value,
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
      this.loadTicket();
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
      const t = this.ticket;
      const body = {
        TicketNumber: t.TicketNumber,
        Folio: t.Folio,
        ShortDescription: t.ShortDescription,
        Description: t.Description,
        CreatedBy: t.CreatedBy,
        Company: t.Company,
        ReportedBy: t.ReportedBy,
        Category: t.Category,
        Subcategory: t.Subcategory,
        Severity: t.Severity,
        Impact: t.Impact,
        Urgency: t.Urgency,
        Priority: t.Priority,
        Status: newStatus,
        Workflow: t.Workflow,
        Channel: t.Channel,
        AssignmentGroup: t.AssignmentGroup,
        AssignedTo: t.AssignedTo,
      };

      const res = await fetch(
        `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.UPDATE_TICKET(this.ticketId)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        }
      );

      if (!res.ok) throw new Error(await res.text());
      this.loadTicket();
    } catch (err) {
      console.error("Error updating ticket status:", err);
      alert("Error al actualizar el estado del ticket");
    }
  }

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
    } catch (err) {
      console.error("Error deleting ticket:", err);
      alert("Error al eliminar el ticket");
    }
  }

  show(id, v) {
    document.getElementById(id)?.classList.toggle("hidden", !v);
  }

  f(d) {
    return d ? new Date(d).toLocaleString("es-MX") : "";
  }

  async deleteAttachment(attachmentId) {
    if (!confirm("¿Eliminar este archivo adjunto?")) return;
  
    try {
      const res = await fetch(
        `/api/tickets/${this.ticketId}/attachments/${attachmentId}`,
        { method: "DELETE" }
      );
      if (!res.ok) throw new Error(await res.text());
      alert("✅ Archivo eliminado correctamente");
      this.loadAttachments(); // Refrescar lista
    } catch (err) {
      console.error("Error eliminando adjunto:", err);
      alert("❌ No se pudo eliminar el archivo");
    }
  }

}

/* init */
document.addEventListener("DOMContentLoaded", () => new TicketDetailManager());