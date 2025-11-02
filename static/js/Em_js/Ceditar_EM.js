// ==========================
// Guardar valores originales
// ==========================
const originalValues = {};

window.addEventListener("load", () => {
  document.querySelectorAll("input").forEach(input => {
    originalValues[input.id] = input.value;
  });
});

// ==========================
// Modal
// ==========================
function mostrarModal(mensaje, tipo = "success") {
  const modalText = document.getElementById("modal-text");
  modalText.textContent = mensaje;
  modalText.className = tipo;
  document.getElementById("modal").style.display = "flex";
}

function cerrarModal() {
  document.getElementById("modal").style.display = "none";
}

// ==========================
// Validar formulario
// ==========================
function validarFormulario() {
  let cambios = false;
  document.querySelectorAll("input").forEach(input => {
    if (input.value !== originalValues[input.id]) cambios = true;
  });
  return cambios;
}

// ==========================
// Enviar formulario
// ==========================
const editarForm = document.getElementById("editarForm");
editarForm?.addEventListener("submit", async function(e) {
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
    const response = await fetch("/Ad_Ceditar", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(data)
    });

    const result = await response.json().catch(async () => {
      console.error("Error parseando JSON:", await response.text());
      return;
    });

    if (result?.success) {
      mostrarModal("Usuario actualizado correctamente", "success");
    } else {
      mostrarModal("Error al actualizar", "error");
    }
  } catch (err) {
    console.error("Error en la petición:", err);
    mostrarModal("Error en la conexión", "error");
  }
});

// ==========================
// Subir / Eliminar foto
// ==========================
const profileImg = document.querySelector(".profile-section img");
const subirBtn = document.querySelector(".profile-btn:not(.delete)");
const eliminarBtn = document.querySelector(".profile-btn.delete");

// Crear input oculto
const fileInput = document.createElement("input");
fileInput.type = "file";
fileInput.accept = "image/*";
fileInput.style.display = "none";
document.body.appendChild(fileInput);

// Subir foto
subirBtn?.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", async () => {
  if (!fileInput.files.length) return;

  const formData = new FormData();
  formData.append("foto", fileInput.files[0]);

  try {
    const response = await fetch("/Em_Ceditar_foto", { method: "POST", body: formData });

    if (response.status === 401) {
      Swal.fire('Sesión expirada', 'Por favor vuelve a iniciar sesión', 'warning')
      .then(() => window.location.href = '/login');
      return;
    }

    const data = await response.json();
    if (data.success) {
      profileImg.src = data.photo_url;
      Swal.fire('Éxito', 'Foto actualizada correctamente', 'success');
    } else {
      throw new Error(data.msg || "Error desconocido");
    }
  } catch (error) {
    console.error("Error:", error);
    Swal.fire('Error', error.message || 'No se pudo subir la foto', 'error');
  }
});

// Eliminar foto
eliminarBtn?.addEventListener("click", async () => {
  try {
    const response = await fetch("/Em_Ceditar_foto", {
      method: "DELETE",
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });

    if (response.status === 401) {
      Swal.fire('Sesión expirada', 'Por favor vuelve a iniciar sesión', 'warning')
      .then(() => window.location.href = '/login');
      return;
    }

    const data = await response.json();
    if (data.success) {
      profileImg.src = data.photo_url;
      Swal.fire('Éxito', 'Foto eliminada correctamente', 'success');
    } else {
      throw new Error(data.msg || "Error desconocido");
    }
  } catch (error) {
    console.error("Error:", error);
    Swal.fire('Error', error.message || 'No se pudo eliminar la foto', 'error');
  }
});

// ==========================
// Recuperar contraseña (global)
// ==========================
window.recuperarContrasena = async function() {
  try {
    const { value: nombre } = await Swal.fire({
      title: 'Recuperar contraseña',
      input: 'text',
      inputLabel: 'Ingresa tu nombre de usuario',
      inputPlaceholder: 'Ejemplo: admin1',
      showCancelButton: true,
      confirmButtonText: 'Continuar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#e60000',
      cancelButtonColor: '#888',
      preConfirm: (value) => {
        if (!value || value.trim() === '') Swal.showValidationMessage('Debes ingresar tu nombre de usuario');
        return value;
      }
    });

    if (!nombre) return;

    const { value: telefono } = await Swal.fire({
      title: 'Recuperar contraseña',
      input: 'text',
      inputLabel: 'Ingresa tu número de teléfono',
      inputPlaceholder: 'Ejemplo: 3001234567',
      showCancelButton: true,
      confirmButtonText: 'Enviar código',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#e60000',
      cancelButtonColor: '#888',
      preConfirm: (value) => {
        if (!value || value.trim() === '') Swal.showValidationMessage('Debes ingresar un número de teléfono válido');
        return value;
      }
    });

    if (!telefono) return;

    let telefonoFormateado = telefono.trim();
    if (!telefonoFormateado.startsWith("+57")) telefonoFormateado = "+57" + telefonoFormateado;

    const res = await fetch("/enviar_token_recuperacion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telefono: telefonoFormateado })
    });
    const data = await res.json();
    if (!data.success) return Swal.fire('❌ Error', data.msg, 'error');

    await Swal.fire('✅ Código enviado', 'Revisa tu teléfono para ver el código de verificación.', 'success');

    const { value: token } = await Swal.fire({
      title: 'Verificación',
      input: 'text',
      inputLabel: 'Ingresa el código recibido',
      inputPlaceholder: 'Ejemplo: 123456',
      showCancelButton: true,
      confirmButtonText: 'Validar código',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#e60000',
      cancelButtonColor: '#888',
      preConfirm: (value) => {
        if (!value || value.trim().length < 4) Swal.showValidationMessage('Debes ingresar el código recibido');
        return value;
      }
    });

    if (!token) return;

    const { value: nuevaContrasena } = await Swal.fire({
      title: 'Nueva contraseña',
      input: 'password',
      inputLabel: 'Ingresa tu nueva contraseña',
      inputPlaceholder: '********',
      inputAttributes: { minlength: 6 },
      showCancelButton: true,
      confirmButtonText: 'Actualizar contraseña',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#e60000',
      cancelButtonColor: '#888',
      preConfirm: (value) => {
        if (!value || value.length < 6) Swal.showValidationMessage('La contraseña debe tener al menos 6 caracteres');
        return value;
      }
    });

    if (!nuevaContrasena) return;

    const resp = await fetch("/Em_validar_token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, telefono, token, nueva_clave: nuevaContrasena })
    });
    const resultado = await resp.json();
    if (resultado.success) Swal.fire('🎉 Éxito', 'Contraseña actualizada correctamente', 'success');
    else Swal.fire('❌ Error', resultado.msg, 'error');

  } catch (err) {
    console.error("Error en la recuperación de contraseña:", err);
    Swal.fire('❌ Error', 'No se pudo conectar con el servidor', 'error');
  }
};
