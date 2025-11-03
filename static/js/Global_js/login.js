// 🎴 ALERTA LOGIN TIPO NOTIFICACIÓN
function alertaLoginNotif(icon, title, message) {
    Swal.fire({
        toast: true,               // Tipo notificación
        position: 'top-end',       // Esquina superior derecha
        showConfirmButton: false,  // Sin botón
        timer: 2000,               // Desaparece sola en 2s
        timerProgressBar: true,    // Barra de progreso
        icon: icon,                // "success", "error", "warning", "info"
        title: title,
        text: message || "",
        background: "#1a1a1a",
        color: "#fff",
        iconColor: icon === "success" ? "#00ff99" : icon === "error" ? "#ff3333" : "#ffcc00",
        showClass: {
            popup: 'swal2-toast-show'
        },
        hideClass: {
            popup: 'swal2-toast-hide'
        }
    });
}

// Animaciones personalizadas para notificación
const styleNotif = document.createElement("style");
styleNotif.innerHTML = `
  .swal2-toast-show {
    animation: toastFadeIn 0.4s ease-out forwards;
  }
  .swal2-toast-hide {
    animation: toastFadeOut 0.3s ease-in forwards;
  }
  @keyframes toastFadeIn {
    0% { transform: translateY(-20px); opacity: 0; }
    100% { transform: translateY(0); opacity: 1; }
  }
  @keyframes toastFadeOut {
    0% { transform: translateY(0); opacity: 1; }
    100% { transform: translateY(-20px); opacity: 0; }
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
        alertaLoginNotif("warning", "Campos incompletos", "Por favor completa todos los campos.");
        return false;
    }

    if (role === "Empleado") {
        branch = document.getElementById("branch").value;
        if (!branch) {
            alertaLoginNotif("warning", "Sucursal requerida", "Por favor selecciona una sucursal.");
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
            alertaLoginNotif("success", "Bienvenido", data.msg || "Inicio de sesión exitoso");
            setTimeout(() => {
                window.location.href = data.redirect || "/";
            }, 1000);
        } else {
            alertaLoginNotif("error", "Error", data.msg || "Usuario o contraseña incorrecta");
        }

    } catch (err) {
        console.error(err);
        alertaLoginNotif("error", "Error", "Ocurrió un problema al intentar conectarse.");
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
