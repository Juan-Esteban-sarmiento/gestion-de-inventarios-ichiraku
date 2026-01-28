/* ============================================
   🎴 ALERTA NINJA GLOBAL - PREMIUM RE-ENGINEERING
   ============================================ */

/**
 * Muestra una alerta con diseño Ninja Premium adaptada al aplicativo.
 * @param {string} icon - 'success', 'error', 'warning', 'info', 'question'
 * @param {string} title - Título del mensaje
 * @param {string} text - Contenido del mensaje
 */
function alertaNinja(icon, title, text) {
  const iconColors = {
    success: '#ff0000',
    error: '#b30000',
    warning: '#e60000',
    info: '#ffffff',
    question: '#ff3333'
  };

  return Swal.fire({
    icon: icon,
    title: title,
    text: text || '',
    background: 'rgba(10, 10, 10, 0.95)',
    color: '#dddddd',
    iconColor: iconColors[icon] || '#ff0000',
    confirmButtonText: 'ENTENDIDO',
    buttonsStyling: false,
    customClass: {
      popup: 'ninja-swal-popup',
      title: 'ninja-swal-title',
      htmlContainer: 'ninja-swal-text',
      confirmButton: 'ninja-swal-confirm',
      cancelButton: 'ninja-swal-cancel'
    },
    showClass: {
      popup: 'ninja-animate-in'
    },
    hideClass: {
      popup: 'ninja-animate-out'
    }
  });
}

/**
 * Alerta personalizada para modales con inputs (ej. Editar)
 */
function alertaNinjaFire(options) {
  const defaults = {
    background: 'rgba(10, 10, 10, 0.98)',
    color: '#dddddd',
    buttonsStyling: false,
    customClass: {
      popup: 'ninja-swal-popup',
      title: 'ninja-swal-title',
      htmlContainer: 'ninja-swal-text',
      confirmButton: 'ninja-swal-confirm',
      cancelButton: 'ninja-swal-cancel',
      input: 'ninja-swal-input'
    },
    showClass: { popup: 'ninja-animate-in' },
    hideClass: { popup: 'ninja-animate-out' }
  };
  const opts = Object.assign({}, defaults, options);
  return Swal.fire(opts);
}

window.alertaNinja = alertaNinja;
window.alertaNinjaFire = alertaNinjaFire;

/* --- ESTILOS INYECTADOS PARA SWEETALERT2 --- */
const ninjaAlertStyle = document.createElement('style');
ninjaAlertStyle.innerHTML = `
  /* Contenedor Principal */
  .ninja-swal-popup {
    border: 1.5px solid rgba(255, 0, 0, 0.5) !important;
    border-radius: 24px !important;
    padding: 30px !important;
    box-shadow: 0 20px 50px rgba(0,0,0,0.8) !important;
    backdrop-filter: blur(15px) !important;
  }

  /* Títulos (Montserrat para limpieza) */
  .ninja-swal-title {
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    font-size: 20px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 15px !important;
  }

  /* Texto de cuerpo */
  .ninja-swal-text {
    font-family: 'Montserrat', sans-serif !important;
    color: #bbb !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
  }

  /* Botón Confirmar (Estilo Shinobi) */
  .ninja-swal-confirm {
    background: linear-gradient(135deg, #8b0000 0%, #b30000 100%) !important;
    color: #fff !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    padding: 12px 30px !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    cursor: pointer !important;
    text-transform: uppercase !important;
    margin: 10px !important;
    transition: 0.3s !important;
  }

  .ninja-swal-confirm:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(255,0,0,0.3) !important;
    background: #d00 !important;
  }

  /* Botón Cancelar */
  .ninja-swal-cancel {
    background: rgba(255, 255, 255, 0.05) !important;
    color: #aaa !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    padding: 12px 30px !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    cursor: pointer !important;
    text-transform: uppercase !important;
    margin: 10px !important;
    transition: 0.3s !important;
  }

  .ninja-swal-cancel:hover { background: rgba(255, 255, 255, 0.1) !important; color: #fff !important; }

  /* Inputs dentro de modales */
  .swal2-input.ninja-swal-input {
    background: rgba(0, 0, 0, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #fff !important;
    border-radius: 10px !important;
    font-family: 'Montserrat', sans-serif !important;
    font-size: 14px !important;
  }

  /* 🔥 MEJORA: Estilo Premium para Seleccionar Archivo 🔥 */
  .swal2-file.ninja-swal-input {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1.5px dashed rgba(255, 0, 0, 0.3) !important;
    color: #888 !important;
    font-family: 'Montserrat', sans-serif !important;
    font-size: 12px !important;
    padding: 10px !important;
    cursor: pointer !important;
    border-radius: 12px !important;
    width: 100% !important;
    margin-top: 10px !important;
  }

  .swal2-file.ninja-swal-input::file-selector-button {
    background: var(--red-brand) !important;
    color: #fff !important;
    border: none !important;
    padding: 8px 15px !important;
    border-radius: 8px !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    font-size: 10px !important;
    margin-right: 15px !important;
    cursor: pointer !important;
    transition: 0.3s !important;
  }

  .swal2-file.ninja-swal-input::file-selector-button:hover {
    background: #d00 !important;
    box-shadow: 0 0 10px rgba(255, 0, 0, 0.3) !important;
  }

  /* Animaciones */
  .ninja-animate-in { animation: ninjaPopIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
  .ninja-animate-out { animation: ninjaPopOut 0.3s ease-in forwards; }

  @keyframes ninjaPopIn {
    0% { transform: scale(0.5); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
  }
  @keyframes ninjaPopOut {
    0% { transform: scale(1); opacity: 1; }
    100% { transform: scale(0.8); opacity: 0; }
  }
`;
document.head.appendChild(ninjaAlertStyle);
