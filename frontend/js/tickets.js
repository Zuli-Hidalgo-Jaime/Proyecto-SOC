console.log("CONFIG en tickets.js:", window.CONFIG);

class TicketsManager {
  constructor() {
    this.tickets   = [];
    this.filtered  = [];
    this.load();
    this.bindEvents();
    setInterval(() => this.load(), CONFIG.UI.AUTO_REFRESH_INTERVAL);
  }

  async load() {
    try {
      this.toggle("loading", true);
      const url = `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.TICKETS}`;
      const res = await fetch(url, {
        headers: {
          ...getAuthHeader()  
        }
      });
      if (!res.ok) throw new Error(await res.text());
      this.tickets  = await res.json();
      this.filtered = [...this.tickets];
      this.render();
    } catch (err) {
      console.error(err);
      this.toggle("error", true);
    } finally {
      this.toggle("loading", false);
    }
  }

  bindEvents() {
    const s = document.getElementById("searchInput");
    const f = document.getElementById("statusFilter");
    if (s) {
      let t;
      s.addEventListener("input", () => {
        clearTimeout(t);
        t = setTimeout(() => this.applyFilters(), CONFIG.UI.SEARCH_DELAY);
      });
    }
    f?.addEventListener("change", () => this.applyFilters());
  }

  applyFilters() {
    const term   = (document.getElementById("searchInput")?.value || "").toLowerCase();
    const status = document.getElementById("statusFilter")?.value || "";

    this.filtered = this.tickets.filter(t => {
      const text = !term || t.ShortDescription.toLowerCase().includes(term) ||
                            (t.Description || "").toLowerCase().includes(term);
      const st   = !status || t.Status === status;
      return text && st;
    });
    this.render();
  }

  render() {
    const tbody = document.getElementById("ticketsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (this.filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:2rem;">No se encontraron tickets</td></tr>`;
      return;
    }
    this.filtered.forEach(t => tbody.appendChild(this.row(t)));
  }

  row(t) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${t.id}</td>
      <td>${t.TicketNumber}</td>
      <td><a href="ticket-detail.html?id=${t.id}">${this.html(t.ShortDescription)}</a></td>
      <td><span class="status-badge">${t.Status}</span></td>
      <td>${t.Priority   || ""}</td>
      <td>${t.AssignedTo || ""}</td>
      <td>${this.f(t.CreatedAt)}</td>
      <td><button class="btn btn-danger btn-sm" onclick="deleteTicket(${t.id})">Eliminar</button></td>`;
    return tr;
  }

  /* helpers */
  toggle(id, s){ document.getElementById(id)?.classList.toggle("hidden", !s); }
  f(d){ return d ? new Date(d).toLocaleString("es-MX") : ""; }
  html(t){ const div=document.createElement("div"); div.textContent=t; return div.innerHTML; }
}

async function deleteTicket(id){
  if(!confirm("¿Eliminar ticket?")) return;
  await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.DELETE_TICKET(id)}`,{
    method:"DELETE",
    headers: {
      ...getAuthHeader()  
    }
  });
  location.reload();
}

document.addEventListener("DOMContentLoaded", () => new TicketsManager());
