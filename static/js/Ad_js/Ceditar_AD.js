let originalValues = {};

window.onload = () => {
  document.querySelectorAll("input").forEach(input => {
    originalValues[input.id] = input.value;
  });
};

function mostrarModal(mensaje, tipo="success") {
  const modalText = document.getElementById("modal-text");
  modalText.textContent = mensaje;
  modalText.className = tipo;
  document.getElementById("modal").style.display = "flex";
}

function cerrarModal() {
  document.getElementById("modal").style.display = "none";
}

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
    mostrarModal("No se han hecho cambios", "error");
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
      mostrarModal("Usuario actualizado correctamente", "success");
    } else {
      mostrarModal("Error al actualizar", "error");
    }
  } catch (err) {
    console.error("Error en la petición:", err);
  }
});

// Subir foto
const subirBtn = document.querySelector('.profile-btn:not(.delete)');
const fileInput = document.createElement('input');
fileInput.type = 'file';
fileInput.accept = 'image/*';
fileInput.style.display = 'none';
document.body.appendChild(fileInput);

subirBtn.addEventListener('click', () => {
  fileInput.click();
});

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
    mostrarModal('Foto actualizada', 'success');
  } else {
    mostrarModal('Error al subir foto', 'error');
  }
});

// Eliminar foto
const eliminarBtn = document.querySelector('.profile-btn.delete');
eliminarBtn.addEventListener('click', async function() {
  let response = await fetch('/Ad_Ceditar_foto', {
    method: 'DELETE'
  });
  let result = await response.json();
  if (result.success) {
    document.querySelector('.profile-section img').src = result.photo_url;
    mostrarModal('Foto eliminada', 'success');
  } else {
    mostrarModal('Error al eliminar foto', 'error');
  }
});

async function recuperarContrasena() {
  const { value: nombre } = await Swal.fire({
    title: 'Recuperar contraseña',
    input: 'text',
    inputLabel: 'Ingresa tu nombre de usuario (Administrador)',
    inputPlaceholder: 'Ejemplo: admin1',
    showCancelButton: true,
    confirmButtonText: 'Continuar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#e60000',
    cancelButtonColor: '#888',
    preConfirm: (value) => {
      if (!value || value.trim() === '') {
        Swal.showValidationMessage('Debes ingresar tu nombre de usuario');
      }
      return value;
    }
  });

  // 1️⃣ Pedir teléfono
  const { value: telefono } = await Swal.fire({
    title: 'Recuperar contraseña',
    input: 'text',
    inputLabel: 'Ingresa el número de teléfono donde recibirás el código',
    inputPlaceholder: 'Ejemplo: 3001234567',
    showCancelButton: true,
    confirmButtonText: 'Enviar código',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#e60000',
    cancelButtonColor: '#888',
    preConfirm: (value) => {
      if (!value || value.trim() === '') {
        Swal.showValidationMessage('Debes ingresar un número de teléfono válido');
      }
      return value;
    }
  });

  if (!telefono) return;

  try {
    // 2️⃣ Enviar token al backend
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
      return Swal.fire('❌ Error', data.msg, 'error');
    }

    await Swal.fire('✅ Código enviado', 'Revisa tu teléfono para ver el código de verificación.', 'success');

    // 3️⃣ Pedir el token recibido por SMS
    const { value: token } = await Swal.fire({
      title: 'Verificación',
      input: 'text',
      inputLabel: 'Ingresa el código recibido en tu teléfono',
      inputPlaceholder: 'Ejemplo: 123456',
      showCancelButton: true,
      confirmButtonText: 'Validar código',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#e60000',
      cancelButtonColor: '#888',
      preConfirm: (value) => {
        if (!value || value.trim().length < 4) {
          Swal.showValidationMessage('Debes ingresar el código recibido');
        }
        return value;
      }
    });

    if (!token) return;

    // 4️⃣ Pedir nueva contraseña
    const { value: nuevaContrasena } = await Swal.fire({
      title: 'Nueva contraseña',
      input: 'password',
      inputLabel: 'Ingresa tu nueva contraseña',
      inputPlaceholder: '********',
      inputAttributes: {
        minlength: 6,
      },
      showCancelButton: true,
      confirmButtonText: 'Actualizar contraseña',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#e60000',
      cancelButtonColor: '#888',
      preConfirm: (value) => {
        if (!value || value.length < 6) {
          Swal.showValidationMessage('La contraseña debe tener al menos 6 caracteres');
        }
        return value;
      }
    });

    if (!nuevaContrasena) return;

    // 5️⃣ Enviar al backend para validar token y actualizar la contraseña
    const resp = await fetch("/validar_token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, telefono, token, nueva_clave: nuevaContrasena })
    });

    const resultado = await resp.json();

    if (resultado.success) {
      Swal.fire('🎉 Éxito', 'Tu contraseña se actualizó correctamente.', 'success');
    } else {
      Swal.fire('❌ Error', resultado.msg, 'error');
    }

  } catch (err) {
    console.error("Error en la petición:", err);
    Swal.fire('❌ Error', 'No se pudo conectar con el servidor', 'error');
  }
}


