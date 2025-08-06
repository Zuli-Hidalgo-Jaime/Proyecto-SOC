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

  async loadTicket() {
    try {
      this.show("loading", true);
      const res = await fetchWithAuth(
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
    badge.className = `status-badge status-${t.Status.toLowerCase().replace(/\s/g, '_')}`;
    this.show("ticketDetail", true);
    this.loadAttachments();
    this.loadHistory();
    this.show("ticketDetail", true);
  }

  async loadAttachments() {
    const container = document.getElementById("attachments-list");
    container.innerHTML = "";
    try {
      const response = await fetchWithAuth(
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

  bindEvents() {
    document.getElementById("editTicket")?.addEventListener("click", () => this.showEditModal());
    document.getElementById("changeStatus")?.addEventListener("click", () => this.showStatusDialog());
    document.getElementById("deleteTicket")?.addEventListener("click", () => this.confirmDelete());
    document.getElementById("closeEditModal")?.addEventListener("click", () => this.hideEditModal());
    document.getElementById("cancelEdit")?.addEventListener("click", () => this.hideEditModal());
    document.getElementById("editTicketForm")?.addEventListener("submit", (e) => {
      e.preventDefault();
      this.submitEdit();
    });
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

  async uploadAttachment() {
    const input = document.getElementById("attachmentInput");
    if (!input.files.length) {
      alert("📎 Por favor selecciona un archivo.");
      return;
    }
    const formData = new FormData();
    formData.append("file", input.files[0]);
    try {
      const res = await fetchWithAuth(
        `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.UPLOAD_ATTACHMENT(this.ticketId)}`,
        {
          method: "POST",
          body: formData
        }
      );
      if (!res.ok) throw new Error(await res.text());
      alert("✅ Archivo subido correctamente");
      this.loadTicket();
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
      const res = await fetchWithAuth(
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
      const res = await fetchWithAuth(
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
      const res = await fetchWithAuth(
        `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.DELETE_TICKET(this.ticketId)}`,
        {
          method: "DELETE"
        }
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
      const res = await fetchWithAuth(
        `/api/tickets/${this.ticketId}/attachments/${attachmentId}`,
        { method: "DELETE" }
      );
      if (!res.ok) throw new Error(await res.text());
      alert("✅ Archivo eliminado correctamente");
      this.loadAttachments();
    } catch (err) {
      console.error("Error eliminando adjunto:", err);
      alert("❌ No se pudo eliminar el archivo");
    }
  }

  async loadHistory() {
    const container = document.getElementById("ticketHistory");
    container.innerHTML = "Cargando historial...";
    try {
      const res = await fetchWithAuth(
        `${CONFIG.API_BASE_URL}/api/tickets/${this.ticketId}/history`
      );
      if (!res.ok) throw new Error(await res.text());
      const history = await res.json();
      if (!history.length) {
        container.innerHTML = "<i>No hay historial disponible para este ticket.</i>";
        return;
      }
      const grouped = {};
      for (const h of history) {
        if (!grouped[h.field_changed]) grouped[h.field_changed] = [];
        grouped[h.field_changed].push(h);
      }
      container.innerHTML = `
        <ul style="list-style:none; padding:0; margin:0;">
        ${Object.entries(grouped).map(([field, changes], idx) => `
          <li style="margin-bottom:14px;">
            <button
              class="btn btn-secondary"
              style="width:100%; text-align:left; border-radius:6px 6px 0 0; font-weight:600;"
              onclick="const p=document.getElementById('histField${idx}');p.classList.toggle('hidden');"
              type="button"
            >
              ${field} <span style="font-size:13px; font-weight:400;">(${changes.length} cambio${changes.length > 1 ? 's' : ''})</span>
            </button>
            <div id="histField${idx}" class="hidden" style="padding:12px 12px 0 12px; background:#f4f6fb; border-radius:0 0 6px 6px;">
              <ul style="padding-left:0; list-style:none;">
              ${changes.map(change => `
                <li style="margin-bottom:10px;">
                  <span style="color:#888; text-decoration:line-through;">"${change.old_value}"</span>
                  <span style="font-weight:bold; color:#009;">→ "${change.new_value}"</span>
                  <br>
                  <span style="font-size:12px; color:#555;">${change.changed_by || "Sistema"} el ${change.changed_at}</span>
                </li>
              `).join("")}
              </ul>
            </div>
          </li>
        `).join("")}
        </ul>
      `;
    } catch (e) {
      container.innerHTML = "Error al cargar historial";
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new TicketDetailManager();
  document.getElementById("logoutBtn")?.addEventListener("click", () => {
    localStorage.removeItem("token");
    window.location.href = "login.html";
  });
});
