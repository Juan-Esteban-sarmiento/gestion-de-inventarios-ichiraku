/**
 * 🕵️‍♂️ Ichiraku Session Timeout Manager
 * Monitorea la actividad del usuario y cierra la sesion tras inactividad.
 */

let inactivityTimer;
const TIMEOUT_DURATION = 15 * 60 * 1000; // 15 minutos en milisegundos

function resetInactivityTimer() {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(triggerLogout, TIMEOUT_DURATION);
}

function triggerLogout() {
    // Redirigir al logout con un parametro para indicar que fue por inactividad
    window.location.href = '/logout?timeout=1';
}

// Escuchar eventos de interaccion humana
const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];

activityEvents.forEach(event => {
    document.addEventListener(event, resetInactivityTimer, true);
});

// Inicializar el timer al cargar
document.addEventListener('DOMContentLoaded', () => {
    resetInactivityTimer();
    startSessionPolling();
});

// 🔄 Polling para detectar cierres de sesion desde el servidor (ej: otro dispositivo)
function startSessionPolling() {
    setInterval(async () => {
        try {
            const res = await fetch('/api/check_session', {
                headers: {
                    'Accept': 'application/json'
                }
            });
            if (res.status === 401) {
                const data = await res.json();
                if (data.redirect) {
                    window.location.href = data.redirect;
                } else {
                    window.location.reload();
                }
            } else if (res.redirected) {
                // If it redirected without JSON, follow it
                window.location.href = res.url;
            }
        } catch (e) {
            console.error("Error checking session:", e);
        }
    }, 5000); // Consultar cada 5 segundos
}
