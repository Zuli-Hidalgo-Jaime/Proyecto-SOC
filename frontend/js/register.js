// frontend/js/register.js

document.getElementById("register-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    
    const username  = document.getElementById("username").value;
    const password  = document.getElementById("password").value;
    const full_name = document.getElementById("full_name").value;
    const email     = document.getElementById("email").value;
    const errorDiv   = document.getElementById("register-error");
    const successDiv = document.getElementById("register-success");
    errorDiv.textContent = "";
    successDiv.textContent = "";

    try {
        const response = await fetch(CONFIG.API_BASE_URL + "/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username,
                password,
                full_name,
                email
            })
        });

        if (response.ok) {
            successDiv.textContent = "Usuario registrado exitosamente. Ahora puedes iniciar sesión.";
            setTimeout(() => window.location.href = "login.html", 1500);
        } else {
            const err = await response.json();
            errorDiv.textContent = err.detail || "Error al registrar usuario";
        }
    } catch (err) {
        errorDiv.textContent = "Error de conexión con el servidor.";
    }
});
