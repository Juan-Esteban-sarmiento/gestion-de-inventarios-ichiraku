// 🎴 ALERTA LOGIN TIPO NOTIFICACION (PREMIUM STYLED)
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

// 🌟 FUNCION LOGIN CON ALERTA TIPO NOTIFICACION
async function login(event) {
    if (event) event.preventDefault();

    const id = document.getElementById("id").value.trim();
    const password = document.getElementById("password").value.trim();
    const branch = document.getElementById("branch").value;

    // Validaciones
    if (!id || !password) {
        alertaLoginNotif("warning", "DATOS INCOMPLETOS", "Por favor ingresa tu ID y contrasena.");
        return false;
    }

    try {
        const res = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, password, branch })
        });

        const data = await res.json();

        if (data.success) {
            alertaLoginNotif("success", "BIENVENIDO", data.msg || "Inicio de sesion exitoso");
            setTimeout(() => {
                window.location.href = data.redirect || "/";
            }, 1000);
        } else {
            alertaLoginNotif("error", "ERROR", data.msg || "Usuario o contrasena incorrecta");
        }

    } catch (err) {
        console.error(err);
        alertaLoginNotif("error", "ERROR", "Ocurrio un problema al intentar conectarse.");
    }
}

// 🔑 RECUPERACION CON LLAVE MAESTRA
function mostrarRecuperacionLlave() {
    Swal.fire({
        title: '<div class="ninja-recovery-title">⛩️ RECUPERACION NINJA</div>',
        html: `
            <div class="ninja-fb-group">
                <label class="ninja-fb-label">ID / Cedula</label>
                <input id="rec-id" class="ninja-fb-input" placeholder="Ingresa tu ID">
            </div>
            
            <div class="ninja-fb-group">
                <label class="ninja-fb-label">Llave Maestra</label>
                <input id="rec-key" class="ninja-fb-input" placeholder="Tu clave de 12 caracteres" style="text-transform: uppercase;">
            </div>
            
            <div class="ninja-fb-group">
                <label class="ninja-fb-label">Nueva Contrasena</label>
                <input id="rec-pass" type="password" class="ninja-fb-input" placeholder="Minimo 8 caracteres">
            </div>
        `,
        background: 'transparent',
        showCancelButton: true,
        confirmButtonText: 'ACTUALIZAR CLAVE',
        cancelButtonText: 'CANCELAR',
        customClass: {
            popup: 'ninja-recovery-popup',
            confirmButton: 'ninja-rec-confirm',
            cancelButton: 'ninja-rec-cancel'
        },
        buttonsStyling: false,
        backdrop: `rgba(0,0,0,0.9)`,
        allowOutsideClick: false,
        preConfirm: () => {
            const id = document.getElementById('rec-id').value.trim();
            const llave = document.getElementById('rec-key').value.trim().toUpperCase();
            const pass = document.getElementById('rec-pass').value.trim();
            
            if (!id || !llave || !pass) {
                Swal.showValidationMessage('Todos los campos son obligatorios');
                return false;
            }
            if (pass.length < 8) {
                Swal.showValidationMessage('La nueva clave debe tener al menos 8 caracteres');
                return false;
            }
            return { id, llave, nueva_clave: pass };
        }
    }).then(async (result) => {
        if (result.isConfirmed) {
            try {
                const res = await fetch('/recuperar_con_llave', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(result.value)
                });
                const data = await res.json();
                if (data.success) {
                    alertaNinja('success', 'LOGRADO!', 'Tu clave ha sido actualizada. Ya puedes iniciar sesion.');
                } else {
                    alertaNinja('error', 'FALLO', data.msg);
                }
            } catch (e) {
                alertaNinja('error', 'ERROR', 'Fallo en la conexion.');
            }
        }
    });
}

function logout() {
    fetch('/logout', { method: 'GET' })
        .then(() => {
            window.location.href = '/login';
        })
        .catch(err => console.error('Error al cerrar sesion:', err));
}

// La pestana de "rol" fue eliminada; cargarLocales se llama automaticamente.


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

// 🕒 Detectar si la sesion se cerro por inactividad o desde otro dispositivo
function checkSessionTimeout() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('timeout') === '1') {
        const reason = urlParams.get('reason');
        let title = 'SESION CERRADA';
        let message = 'Tu sesion ha expirado por inactividad. Por favor, ingresa de nuevo.';
        let icon = 'info';
        
        if (reason) {
            message = reason;
            if (reason.toLowerCase().includes('otro dispositivo')) {
                title = 'ALERTA DE SEGURIDAD';
                icon = 'warning';
                message += ' Por favor, inicia sesion de nuevo si fuiste tu.';
            } else if (reason.toLowerCase().includes('deshabilitada')) {
                title = 'CUENTA DESHABILITADA';
                icon = 'error';
                message += ' Contacta al administrador.';
            }
        }

        // Usar la alerta Premium ya estandarizada
        alertaNinja(icon, title, message);

        // Limpiar la URL para evitar que el mensaje se repita al recargar
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        checkSessionTimeout();
        cargarLocales();
    });
} else {
    checkSessionTimeout();
    cargarLocales();
}

