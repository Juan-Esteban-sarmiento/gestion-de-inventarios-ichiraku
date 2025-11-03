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
    title: `<span style="font-family:njnaruto; color:#fff; font-size:24px;">${title}</span>`,
    text: text || '',
    background: '#000',
    color: '#fff',
    iconColor: iconColors[icon] || '#ff2a2a',
    confirmButtonColor: '#e60000',
    confirmButtonText: '<span style="font-family:njnaruto;">Aceptar</span>',
    buttonsStyling: false,
    showClass: {
      popup: 'swal2-show-custom'
    },
    hideClass: {
      popup: 'swal2-hide-custom'
    },
    didRender: () => {
      const btn = Swal.getConfirmButton();
      if (btn) {
        btn.style.background = '#e60000';
        btn.style.color = '#fff';
        btn.style.fontWeight = 'bold';
        btn.style.border = '2px solid #ff0000';
        btn.style.borderRadius = '10px';
        btn.style.padding = '8px 18px';
        btn.style.cursor = 'pointer';
        btn.style.transition = 'all 0.3s ease';
        btn.style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.4)';
        
        btn.addEventListener('mouseenter', () => {
          btn.style.background = '#ff0000';
          btn.style.boxShadow = '0 0 15px rgba(255, 0, 0, 0.6)';
          btn.style.transform = 'scale(1.05)';
        });
        btn.addEventListener('mouseleave', () => {
          btn.style.background = '#e60000';
          btn.style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.4)';
          btn.style.transform = 'scale(1)';
        });
      }
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
