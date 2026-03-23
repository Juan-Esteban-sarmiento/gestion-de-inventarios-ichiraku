let originalValues = {};

window.onload = () => {
  document.querySelectorAll("input").forEach(input => {
    originalValues[input.id] = input.value;
  });
};

function validarFormulario() {
  let cambios = false;
  document.querySelectorAll("input").forEach(input => {
    if (input.value !== originalValues[input.id]) cambios = true;
  });
  return cambios;
}

document.getElementById("editarForm").addEventListener("submit", async function (e) {
  e.preventDefault();
  if (!validarFormulario()) {
    alertaNinja("warning", "Sin cambios", "No se han realizado modificaciones en tu perfil.");
    return;
  }

  const formData = new FormData(this);
  const data = {
    Nombre: formData.get("Nombre")
  };

  try {
    let response = await fetch("/Ad_Ceditar", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(data)
    });
    let result = await response.json();
    if (result.success) {
      alertaNinja("success", "GUARDADO", "Tu información ha sido actualizada.");
      originalValues["Nombre"] = data.Nombre; // Sincronizar para evitar alertas de cambios falsas
    } else {
      alertaNinja("error", "Error", result.msg || "No se pudo actualizar.");
    }
  } catch (err) {
    alertaNinja("error", "Fallo de conexión", "No se pudo conectar con el servidor.");
  }
});

// 🖼 Subir/Cambiar foto
const subirBtn = document.querySelector('.profile-btn:not(.delete)');
const fileInput = document.createElement('input');
fileInput.type = 'file'; fileInput.accept = 'image/*'; fileInput.style.display = 'none';
document.body.appendChild(fileInput);

subirBtn.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', async function () {
  const formData = new FormData();
  formData.append('foto', fileInput.files[0]);
  try {
    let response = await fetch('/Ad_Ceditar_foto', { method: 'POST', body: formData });
    let result = await response.json();
    if (result.success) {
      document.querySelector('.profile-section img').src = result.photo_url;
      alertaNinja('success', 'Foto actualizada', 'Tu nueva foto de perfil está lista.');
    } else {
      alertaNinja('error', 'Error', 'No se pudo subir la imagen.');
    }
  } catch (e) { alertaNinja('error', 'Error', 'Fallo al cargar la foto.'); }
});

// 🗑 Eliminar foto con CONFIRMACIÓN solicitado
const eliminarBtn = document.querySelector('.profile-btn.delete');
eliminarBtn.addEventListener('click', async function () {
  const confirmacion = await alertaNinjaFire({
    icon: 'warning',
    title: 'BORRAR FOTO',
    text: 'Esta acción no se puede deshacer. ¿Estás seguro?',
    showCancelButton: true,
    confirmButtonText: 'BORRAR',
    cancelButtonText: 'CANCELAR'
  });

  if (confirmacion.isConfirmed) {
    try {
      let response = await fetch('/Ad_Ceditar_foto', { method: 'DELETE' });
      let result = await response.json();
      if (result.success) {
        document.querySelector('.profile-section img').src = result.photo_url;
        alertaNinja('success', 'Foto eliminada', 'Se ha restaurado la imagen por defecto.');
      } else {
        alertaNinja('error', 'Error', 'No se pudo eliminar la foto.');
      }
    } catch (e) { alertaNinja('error', 'Fallo', 'Error de conexión.'); }
  }
});

// 🔑 Recuperar/Cambiar contraseña
async function recuperarContrasena() {
  const { value: nombre } = await alertaNinjaFire({
    title: 'Seguridad',
    input: 'text',
    inputLabel: 'Nombre completo o Cédula del Administrador',
    inputPlaceholder: 'Ingresa tu usuario o ID...',
    showCancelButton: true,
    confirmButtonText: 'CONTINUAR',
    cancelButtonText: 'CANCELAR'
  });

  if (!nombre) return;

  const { value: telefono } = await alertaNinjaFire({
    title: 'RECUPERACION',
    input: 'text',
    inputLabel: 'Número de teléfono (WhatsApp)',
    inputPlaceholder: 'Ej: 3001234567',
    showCancelButton: true,
    confirmButtonText: 'ENVIAR CODIGO',
    cancelButtonText: 'VOLVER'
  });

  if (!telefono) return;

  try {
    let tFormateado = telefono.trim();
    if (!tFormateado.startsWith('+57')) tFormateado = '+57' + tFormateado;

    const res = await fetch("/enviar_token_recuperacion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telefono: tFormateado })
    });
    const data = await res.json();
    if (!data.success) return alertaNinja('error', 'Error', data.msg);

    alertaNinja('success', 'Código Enviado', 'Revisa tu WhatsApp para ver el código.');

    const { value: token } = await alertaNinjaFire({
      title: 'VERIFICACION',
      input: 'text',
      inputLabel: 'Código de 6 dígitos',
      inputPlaceholder: '123456',
      showCancelButton: true,
      confirmButtonText: 'VALIDAR',
      cancelButtonText: 'CANCELAR'
    });

    if (!token) return;

    const { value: nuevaContrasena } = await alertaNinjaFire({
      title: 'Nueva Clave',
      input: 'password',
      inputLabel: 'Nueva contraseña segura',
      inputPlaceholder: '********',
      showCancelButton: true,
      confirmButtonText: 'ACTUALIZAR',
      cancelButtonText: 'CANCELAR'
    });

    if (!nuevaContrasena) return;

    const resp = await fetch("/validar_token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, telefono, token, nueva_clave: nuevaContrasena })
    });
    const resultado = await resp.json();
    if (resultado.success) {
      alertaNinja('success', 'EXITO', 'Tu contraseña ha sido cambiada.');
    } else {
      alertaNinja('error', 'Código Inválido', resultado.msg);
    }
  } catch (err) { alertaNinja('error', 'Fallo', 'Error al procesar la clave.'); }
}
