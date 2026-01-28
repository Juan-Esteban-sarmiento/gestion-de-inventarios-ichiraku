/**
 * 🕵️‍♂️ Ichiraku Session Timeout Manager
 * Monitorea la actividad del usuario y cierra la sesión tras inactividad.
 */

let inactivityTimer;
const TIMEOUT_DURATION = 15 * 60 * 1000; // 15 minutos en milisegundos

function resetInactivityTimer() {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(triggerLogout, TIMEOUT_DURATION);
}

function triggerLogout() {
    // Redirigir al logout con un parámetro para indicar que fue por inactividad
    window.location.href = '/logout?timeout=1';
}

// Escuchar eventos de interacción humana
const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];

activityEvents.forEach(event => {
    document.addEventListener(event, resetInactivityTimer, true);
});

// Inicializar el timer al cargar
document.addEventListener('DOMContentLoaded', resetInactivityTimer);
