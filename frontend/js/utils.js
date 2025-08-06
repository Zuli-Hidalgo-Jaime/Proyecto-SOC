// frontend/js/utils.js
function getAuthHeader() {
    const token = localStorage.getItem("token");
    return token ? { "Authorization": `Bearer ${token}` } : {};
}

async function fetchWithAuth(url, options = {}) {
    const headers = { ...getAuthHeader(), ...(options.headers || {}) };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
        localStorage.removeItem("token");
        window.location.href = "login.html";
        throw new Error("Sesión expirada o inválida"); // para cortar la función
    }
    return res;
}