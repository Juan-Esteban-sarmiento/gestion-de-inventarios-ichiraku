let originalValues = {};

window.onload = () => {
  document.querySelectorAll("input").forEach(input => {
    originalValues[input.id] = input.value;
  });
};

function validarFormulario(e) {
  let cambios = false;
  document.querySelectorAll("input").forEach(input => {
    if (input.value !== originalValues[input.id]) {
      cambios = true;
    }
  });
  return cambios;
}

document.getElementById("editarForm").addEventListener("submit", async function(e) {
  e.preventDefault();
  if (!validarFormulario()) {
    alertaNinja("warning", "Sin cambios", "No se han realizado modificaciones.");
    return;
  }

  const formData = new FormData(this);
  const data = {
    Nombre: formData.get("Nombre"),
    Contrasena: formData.get("Contrasena")
  };

  try {
    let response = await fetch("/Ad_Ceditar", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(data)
    });

    let result;
    try {
      result = await response.json();
    } catch (e) {
      let text = await response.text();
      return;
    }

    if (result.success) {
      alertaNinja("success", "Actualización exitosa", "Usuario actualizado correctamente.");
    } else {
      alertaNinja("error", "Error", "No se pudo actualizar el usuario.");
    }
  } catch (err) {
    console.error("Error en la petición:", err);
    alertaNinja("error", "Error", "No se pudo conectar con el servidor.");
  }
});

// 🖼 Subir foto
const subirBtn = document.querySelector('.profile-btn:not(.delete)');
const fileInput = document.createElement('input');
fileInput.type = 'file';
fileInput.accept = 'image/*';
fileInput.style.display = 'none';
document.body.appendChild(fileInput);

subirBtn.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', async function() {
  const formData = new FormData();
  formData.append('foto', fileInput.files[0]);
  let response = await fetch('/Ad_Ceditar_foto', {
    method: 'POST',
    body: formData
  });
  let result = await response.json();
  if (result.success) {
    document.querySelector('.profile-section img').src = result.photo_url;
    alertaNinja('success', 'Foto actualizada', 'Tu foto de perfil ha sido cambiada.');
  } else {
    alertaNinja('error', 'Error', 'No se pudo subir la foto.');
  }
});

// 🗑 Eliminar foto
const eliminarBtn = document.querySelector('.profile-btn.delete');
eliminarBtn.addEventListener('click', async function() {
  let response = await fetch('/Ad_Ceditar_foto', {
    method: 'DELETE'
  });
  let result = await response.json();
  if (result.success) {
    document.querySelector('.profile-section img').src = result.photo_url;
    alertaNinja('success', 'Foto eliminada', 'Tu foto de perfil fue eliminada correctamente.');
  } else {
    alertaNinja('error', 'Error', 'No se pudo eliminar la foto.');
  }
});

// 🔑 Recuperar contraseña (mantiene Swal para entradas)
async function recuperarContrasena() {
  const { value: nombre } = await alertaNinjaFire({
    title: 'Recuperar contraseña',
    input: 'text',
    inputLabel: 'Ingresa tu nombre de usuario (Administrador)',
    inputPlaceholder: 'Ejemplo: admin1',
    showCancelButton: true,
    confirmButtonText: 'Continuar',
    cancelButtonText: 'Cancelar',
    preConfirm: (value) => {
      if (!value || value.trim() === '') {
        Swal.showValidationMessage('Debes ingresar tu nombre de usuario');
      }
      return value;
    }
  });

  if (!nombre) return;

  // 1️⃣ Pedir teléfono
  const { value: telefono } = await alertaNinjaFire({
    title: 'Recuperar contraseña',
    input: 'text',
    inputLabel: 'Ingresa el número de teléfono donde recibirás el código',
    inputPlaceholder: 'Ejemplo: 3001234567',
    showCancelButton: true,
    confirmButtonText: 'Enviar código',
    cancelButtonText: 'Cancelar',
    preConfirm: (value) => {
      if (!value || value.trim() === '') {
        Swal.showValidationMessage('Debes ingresar un número de teléfono válido');
      }
      return value;
    }
  });

  if (!telefono) return;

  try {
    // 2️⃣ Enviar token
    let telefonoFormateado = telefono.trim();
    if (!telefonoFormateado.startsWith('+57')) {
      telefonoFormateado = '+57' + telefonoFormateado;
    }

    const res = await fetch("/enviar_token_recuperacion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telefono: telefonoFormateado })
    });

    const data = await res.json();

    if (!data.success) {
      return alertaNinja('error', 'Error', data.msg);
    }

    alertaNinja('success', 'Código enviado', 'Revisa tu teléfono para ver el código.');

    // 3️⃣ Token recibido
    const { value: token } = await alertaNinjaFire({
      title: 'Verificación',
      input: 'text',
      inputLabel: 'Ingresa el código recibido',
      inputPlaceholder: 'Ejemplo: 123456',
      showCancelButton: true,
      confirmButtonText: 'Validar código',
      cancelButtonText: 'Cancelar',
      preConfirm: (value) => {
        if (!value || value.trim().length < 4) {
          Swal.showValidationMessage('Debes ingresar el código recibido');
        }
        return value;
      }
    });

    if (!token) return;

    // 4️⃣ Nueva contraseña
    const { value: nuevaContrasena } = await alertaNinjaFire({
      title: 'Nueva contraseña',
      input: 'password',
      inputLabel: 'Ingresa tu nueva contraseña',
      inputPlaceholder: '********',
      inputAttributes: { minlength: 6 },
      showCancelButton: true,
      confirmButtonText: 'Actualizar contraseña',
      cancelButtonText: 'Cancelar',
      preConfirm: (value) => {
        if (!value || value.length < 6) {
          Swal.showValidationMessage('Debe tener al menos 6 caracteres');
        }
        return value;
      }
    });

    if (!nuevaContrasena) return;

    // 5️⃣ Validar token y actualizar
    const resp = await fetch("/validar_token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, telefono, token, nueva_clave: nuevaContrasena })
    });

    const resultado = await resp.json();

    if (resultado.success) {
      alertaNinja('success', 'Éxito', 'Tu contraseña se actualizó correctamente.');
    } else {
      alertaNinja('error', 'Error', resultado.msg);
    }

  } catch (err) {
    console.error("Error en la petición:", err);
    alertaNinja('error', 'Error', 'No se pudo conectar con el servidor.');
  }
}
