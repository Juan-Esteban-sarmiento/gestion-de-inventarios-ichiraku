// 🎴 ALERTA NINJA GLOBAL - Paleta negro, blanco y rojo
function alertaNinja(icon, title, text) {
  const iconColors = {
    success: '#ff2a2a',
    error: '#ff4444',
    warning: '#ff4444',
    info: '#ffffff',
    question: '#ff2a2a'
  };

  Swal.fire({
    icon: icon,
    title: `<span style="color:#fff; font-size:24px; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif">${title}</span>`,
    text: text || '',
    // keep these as options in case callers override
    background: '#000',
    color: '#fff',
    iconColor: iconColors[icon] || '#ff2a2a',
    confirmButtonColor: '#e60000',
    confirmButtonText: 'Aceptar',
    buttonsStyling: false,
    showClass: {
      popup: 'swal2-show-custom'
    },
    hideClass: {
      popup: 'swal2-hide-custom'
    }
  });
}

// 🌀 Animaciones personalizadas SweetAlert2
const style = document.createElement('style');
style.innerHTML = `
  .swal2-show-custom {
    animation: ninjaFadeIn 0.4s ease-out forwards;
  }
  .swal2-hide-custom {
    animation: ninjaFadeOut 0.3s ease-in forwards;
  }
  @keyframes ninjaFadeIn {
    0% { transform: scale(0.8); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
  }
  @keyframes ninjaFadeOut {
    0% { transform: scale(1); opacity: 1; }
    100% { transform: scale(0.85); opacity: 0; }
  }
`;
document.head.appendChild(style);

// Add global CSS overrides for SweetAlert2 to ensure consistency even when code calls Swal.fire directly
const globalCss = document.createElement('style');
globalCss.innerHTML = `
  /* Popup background and text */
  .swal2-container .swal2-popup {
    background: #000 !important;
    color: #fff !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6) !important;
  }
  .swal2-title {
    color: #fff !important;
    font-size: 20px !important;
    margin-bottom: 8px !important;
  }
  .swal2-html-container, .swal2-content {
    color: #ddd !important;
    font-size: 14px !important;
  }
  .swal2-popup .swal2-icon {
    box-shadow: none !important;
  }
  .swal2-confirm {
    background: #e60000 !important;
    color: #fff !important;
    font-weight: 700 !important;
    border: 2px solid #ff0000 !important;
    border-radius: 10px !important;
    padding: 8px 18px !important;
    box-shadow: 0 0 10px rgba(255,0,0,0.35) !important;
  }
  .swal2-confirm:hover {
    background: #ff0000 !important;
    box-shadow: 0 0 15px rgba(255,0,0,0.6) !important;
    transform: scale(1.03);
  }
  .swal2-cancel {
    background: #444 !important;
    color: #fff !important;
    border-radius: 8px !important;
    padding: 6px 14px !important;
    border: none !important;
  }
`;
document.head.appendChild(globalCss);

// Helper: call SweetAlert with alertaNinja defaults merged with any options (useful for input modals)
function alertaNinjaFire(options) {
  const defaults = {
    background: '#000',
    color: '#fff',
    showClass: { popup: 'swal2-show-custom' },
    hideClass: { popup: 'swal2-hide-custom' },
    buttonsStyling: false,
    confirmButtonColor: '#e60000'
  };
  const opts = Object.assign({}, defaults, options);
  return Swal.fire(opts);
}

// Expose helper globally so other scripts can call alertaNinjaFire(...) for input dialogs
window.alertaNinjaFire = alertaNinjaFire;
