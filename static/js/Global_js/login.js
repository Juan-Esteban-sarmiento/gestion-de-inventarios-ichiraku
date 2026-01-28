// 🎴 ALERTA LOGIN TIPO NOTIFICACIÓN (PREMIUM STYLED)
function alertaLoginNotif(icon, title, message) {
    Swal.fire({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        icon: icon,
        title: `<span style="color:#fff; font-weight:700; font-family:'Montserrat', sans-serif;">${title}</span>`,
        text: message || "",
        background: 'rgba(15, 15, 15, 0.95)',
        color: '#ccc',
        iconColor: icon === "success" ? "#ff0000" : icon === "error" ? "#8b0000" : "#e60000",
        customClass: {
            popup: 'ninja-swal-toast-popup',
            htmlContainer: 'ninja-swal-text'
        },
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer);
            toast.addEventListener('mouseleave', Swal.resumeTimer);
        }
    });
}

// Estilos extra para los toasts en el login
const styleNotif = document.createElement("style");
styleNotif.innerHTML = `
  .ninja-swal-toast-popup {
    border: 1px solid rgba(255, 0, 0, 0.4) !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;
    backdrop-filter: blur(10px) !important;
  }
  .ninja-swal-text {
    font-family: 'Montserrat', sans-serif !important;
    font-size: 13px !important;
  }
`;
document.head.appendChild(styleNotif);

// 🌟 FUNCIÓN LOGIN CON ALERTA TIPO NOTIFICACIÓN
async function login(event) {
    if (event) event.preventDefault();

    const id = document.getElementById("id").value.trim();
    const password = document.getElementById("password").value.trim();
    const role = document.getElementById("role").value;
    let branch = "";

    // Validaciones
    if (!id || !password || !role) {
        alertaLoginNotif("warning", "DATOS INCOMPLETOS", "Por favor completa todos los campos.");
        return false;
    }

    if (role === "Empleado") {
        branch = document.getElementById("branch").value;
        if (!branch) {
            alertaLoginNotif("warning", "LOCAL REQUERIDO", "Por favor selecciona una sucursal.");
            return false;
        }
    }

    try {
        const res = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, password, role, branch })
        });

        const data = await res.json();

        if (data.success) {
            alertaLoginNotif("success", "BIENVENIDO", data.msg || "Inicio de sesión exitoso");
            setTimeout(() => {
                window.location.href = data.redirect || "/";
            }, 1000);
        } else {
            alertaLoginNotif("error", "ERROR", data.msg || "Usuario o contraseña incorrecta");
        }

    } catch (err) {
        console.error(err);
        alertaLoginNotif("error", "ERROR", "Ocurrió un problema al intentar conectarse.");
    }
}

function logout() {
    fetch('/logout', { method: 'GET' })
        .then(() => {
            window.location.href = '/login';
        })
        .catch(err => console.error('Error al cerrar sesión:', err));
}

// Mostrar select solo si rol = Empleado
function toggleBranch() {
    const role = document.getElementById("role").value;
    const branchGroup = document.getElementById("branch-group");
    branchGroup.style.display = (role === "Empleado") ? "block" : "none";

    if (role === "Empleado") {
        cargarLocales();
    }
}


// Cargar locales desde backend
async function cargarLocales() {
    try {
        const response = await fetch("/get_locales");
        const data = await response.json();
        const select = document.getElementById("branch");

        select.innerHTML = '<option value="">-- Selecciona --</option>';

        if (data.success && data.locales.length > 0) {
            data.locales.forEach(loc => {
                const option = document.createElement("option");
                option.value = loc.id_local; // id real
                option.textContent = loc.nombre;
                select.appendChild(option);
            });
        } else {
            const option = document.createElement("option");
            option.textContent = "No hay locales disponibles";
            option.disabled = true;
            select.appendChild(option);
        }
    } catch (err) {
        console.error("Error al cargar locales:", err);
    }
}

// 🕒 Detectar si la sesión se cerró por inactividad
function checkSessionTimeout() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('timeout') === '1') {
        // Usar la alerta Premium ya estandarizada
        alertaNinja('info', 'SESION CERRADA', 'Tu sesion ha expirado por inactividad. Por favor, ingresa de nuevo.');

        // Limpiar la URL para evitar que el mensaje se repita al recargar
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkSessionTimeout);
} else {
    checkSessionTimeout();
}

