console.log("CONFIG en create-ticket.js:", window.CONFIG);

class CreateTicketManager {
  constructor() {
    this.form = document.getElementById("createTicketForm");
    this.form?.addEventListener("submit", e => this.submit(e));
  }

  async submit(e) {
    e.preventDefault();
    this.t("loading", true);

    try {
      const fd = new FormData(this.form);
      const body = {
        TicketNumber    : null,
        ShortDescription: fd.get("short_description"),
        Description     : fd.get("description"),
        CreatedBy       : fd.get("created_by"),
        Company         : fd.get("company") || null,
        ReportedBy      : fd.get("reported_by") || null,
        Category        : fd.get("category"),
        Subcategory     : fd.get("subcategory") || null,
        Severity        : fd.get("severity"),
        Impact          : fd.get("impact") || null,
        Urgency         : fd.get("urgency") || null,
        Priority        : fd.get("priority") || null,
        Channel         : fd.get("channel"),
        Workflow        : fd.get("workflow") || null,
        AssignmentGroup : fd.get("assignment_group") || null,
        AssignedTo      : fd.get("assigned_to") || null,
        Status          : "Nuevo"
      };

      const url = `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.CREATE_TICKET}`;
      const res = await fetch(url, {
        method : "POST",
        headers: { "Content-Type": "application/json" },
        body   : JSON.stringify(body)
      });
      if (!res.ok) throw new Error(await res.text());

      const saved = await res.json();
      this.t("success", true);
      this.form.reset();
      setTimeout(() => location.href = `ticket-detail.html?id=${saved.id}`, 1200);

    } catch (err) {
      console.error(err);
      this.t("error", true);
    } finally {
      this.t("loading", false);
    }
  }

  t(id, s){ document.getElementById(id)?.classList.toggle("hidden", !s); }
}

document.addEventListener("DOMContentLoaded", () => new CreateTicketManager());
