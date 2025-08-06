
"#frontend/js/login.js"
document.getElementById("login-form").addEventListener("submit", async function (e) {
    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const errorDiv = document.getElementById("login-error");

    errorDiv.textContent = ""; // Limpia errores anteriores

    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem("token", data.access_token); // Guarda el token
            window.location.href = "/frontend/tickets.html"; // Cambia si tienes otro dashboard
        } else {
            errorDiv.textContent = "Credenciales inválidas";
        }
    } catch (err) {
        errorDiv.textContent = "Error de conexión con el servidor";
    }
});
