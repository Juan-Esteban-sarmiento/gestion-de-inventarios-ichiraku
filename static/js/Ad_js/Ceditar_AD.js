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
      alertaNinja("success", "GUARDADO", "Tu informacion ha sido actualizada.");
      // Sincronizar valores originales para evitar alertas de cambios falsas
      originalValues["Nombre"] = data.Nombre;
    } else {
      alertaNinja("error", "Error", result.msg || "No se pudo actualizar.");
    }
  } catch (err) {
    alertaNinja("error", "Fallo de conexion", "No se pudo conectar con el servidor.");
  }
});

// 🖼 Subir/Cambiar foto
const subirBtn = document.getElementById('subirFotoBtn');
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
      alertaNinja('success', 'Foto actualizada', 'Tu nueva foto de perfil esta lista.');
    } else {
      alertaNinja('error', 'Error', 'No se pudo subir la imagen.');
    }
  } catch (e) { alertaNinja('error', 'Error', 'Fallo al cargar la foto.'); }
});

// 🗑 Eliminar foto con CONFIRMACION solicitado
const eliminarBtn = document.getElementById('eliminarFotoBtn');
eliminarBtn.addEventListener('click', async function () {
  const confirmacion = await alertaNinjaFire({
    icon: 'warning',
    title: 'BORRAR FOTO',
    text: 'Esta accion no se puede deshacer. Estas seguro?',
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
    } catch (e) { alertaNinja('error', 'Fallo', 'Error de conexion.'); }
  }
});

// 🔑 Recuperar/Cambiar contrasena
async function recuperarContrasena() {
  const { value: nombre } = await alertaNinjaFire({
    title: 'Seguridad',
    input: 'text',
    inputLabel: 'Nombre completo o Cedula del Administrador',
    inputPlaceholder: 'Ingresa tu usuario o ID...',
    showCancelButton: true,
    confirmButtonText: 'CONTINUAR',
    cancelButtonText: 'CANCELAR'
  });

  if (!nombre) return;

  const { value: telefono } = await alertaNinjaFire({
    title: 'RECUPERACION',
    input: 'text',
    inputLabel: 'Numero de telefono (WhatsApp)',
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

    alertaNinja('success', 'Codigo Enviado', 'Revisa tu WhatsApp para ver el codigo.');

    const { value: token } = await alertaNinjaFire({
      title: 'VERIFICACION',
      input: 'text',
      inputLabel: 'Codigo de 6 digitos',
      inputPlaceholder: '123456',
      showCancelButton: true,
      confirmButtonText: 'VALIDAR',
      cancelButtonText: 'CANCELAR'
    });

    if (!token) return;

    const { value: nuevaContrasena } = await alertaNinjaFire({
      title: 'Nueva Clave',
      input: 'password',
      inputLabel: 'Nueva contrasena segura',
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
      alertaNinja('success', 'EXITO', 'Tu contrasena ha sido cambiada.');
    } else {
      alertaNinja('error', 'Codigo Invalido', resultado.msg);
    }
  } catch (err) { alertaNinja('error', 'Fallo', 'Error al procesar la clave.'); }
}
