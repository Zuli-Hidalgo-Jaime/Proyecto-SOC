console.log("🎯 login.js cargado correctamente");

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                username: username,
                password: password
            })
        });

        if (!response.ok) throw new Error("Credenciales inválidas");

        const data = await response.json();
        localStorage.setItem('token', data.access_token); // Guarda token
        window.location.href = 'index.html'; // Redirige al home
    } catch (err) {
        document.getElementById('login-error').textContent = err.message;
    }
});
