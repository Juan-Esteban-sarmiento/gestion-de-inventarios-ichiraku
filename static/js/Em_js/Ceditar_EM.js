/* ============================================
   🎴 CEDITAR_EM.JS - PREMIUM LOGIC REFINEMENT
   ============================================ */

/**
 * Guarda los valores originales para detectar cambios y evitar peticiones innecesarias.
 */
const originalValues = {};

window.addEventListener("load", () => {
  document.querySelectorAll("input").forEach(input => {
    if (input.id) originalValues[input.id] = input.value;
  });
});

/**
 * Valida si ha habido cambios en los campos editables.
 */
function validarFormulario() {
  let cambios = false;
  document.querySelectorAll("input:not([readonly])").forEach(input => {
    if (input.id && input.value !== originalValues[input.id]) {
      cambios = true;
    }
  });
  return cambios;
}

// ============================================
// 📁 ACTUALIZACION DE PERFIL (NOMBRE/DATOS)
// ============================================
const editarForm = document.getElementById("editarForm");
editarForm?.addEventListener("submit", async function (e) {
  e.preventDefault();

  if (!validarFormulario()) {
    alertaNinja("warning", "SIN CAMBIOS", "No has modificado ningun campo.");
    return;
  }

  const formData = new FormData(this);
  const data = {
    Nombre: formData.get("Nombre"),
    wa_apikey: formData.get("wa_apikey")
  };

  try {
    const response = await fetch("/Ad_Ceditar", { // Se asume que el backend gestiona el rol por sesion
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result?.success) {
      alertaNinja("success", "EXITO", "Tu perfil ha sido actualizado correctamente.");
      // Actualizar originales
      document.querySelectorAll("input").forEach(input => {
        if (input.id) originalValues[input.id] = input.value;
      });
    } else {
      alertaNinja("error", "ERROR", result.msg || "No se pudo actualizar el perfil.");
    }
  } catch (err) {
    console.error("Error en la peticion:", err);
    alertaNinja("error", "ERROR DE CONEXION", "No se pudo contactar con el servidor.");
  }
});

// ============================================
// 📸 GESTION DE FOTO DE PERFIL
// ============================================
const profileImg = document.querySelector(".profile-section img");
const subirBtn = document.querySelector(".profile-btn:not(.delete)");
const eliminarBtn = document.querySelector(".profile-btn.delete");

// Input oculto para carga de archivos
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

  // Alerta de carga
  alertaNinja("info", "CARGANDO", "Subiendo tu nueva foto...");

  try {
    const response = await fetch("/Em_Ceditar_foto", { method: "POST", body: formData });

    if (response.status === 401) {
      alertaNinja("warning", "SESION EXPIRADA", "Por favor ingresa de nuevo.")
        .then(() => window.location.href = '/login');
      return;
    }

    const data = await response.json();
    if (data.success) {
      profileImg.src = data.photo_url;
      alertaNinja("success", "ESTILO SHINOBI", "Tu foto ha sido actualizada.");
    } else {
      throw new Error(data.msg || "Error al subir la imagen.");
    }
  } catch (error) {
    console.error("Error:", error);
    alertaNinja("error", "ERROR", error.message || "No se pudo actualizar la foto.");
  }
});

// Eliminar foto
eliminarBtn?.addEventListener("click", async () => {
  const confirmacion = await alertaNinjaFire({
    title: 'ELIMINAR FOTO?',
    text: "Tu perfil volvera a la imagen por defecto.",
    icon: 'question',
    showCancelButton: true,
    confirmButtonText: 'ELIMINAR',
    cancelButtonText: 'CANCELAR'
  });

  if (!confirmacion.isConfirmed) return;

  try {
    const response = await fetch("/Em_Ceditar_foto", {
      method: "DELETE",
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });

    if (response.status === 401) {
      window.location.href = '/login';
      return;
    }

    const data = await response.json();
    if (data.success) {
      profileImg.src = "/static/image/default.png";
      alertaNinja("success", "MODIFICADO", "Has eliminado tu foto de perfil.");
    } else {
      throw new Error(data.msg || "Error al eliminar.");
    }
  } catch (error) {
    console.error("Error:", error);
    alertaNinja("error", "ERROR", "No se pudo borrar la foto.");
  }
});

// ============================================
// 🔑 RECUPERACION / CAMBIO DE CLAVE (NINJA FLOW)
// ============================================
window.recuperarContrasena = async function () {
  try {
    // 1. Nombre de Usuario
    const { value: nombre } = await alertaNinjaFire({
      title: 'RECUPERAR CLAVE',
      input: 'text',
      inputLabel: 'Nombre completo o Cedula del Empleado',
      inputPlaceholder: 'Ingresa tu usuario o ID...',
      showCancelButton: true,
      confirmButtonText: 'SIGUIENTE',
      preConfirm: (value) => {
        if (!value || value.trim() === '') Swal.showValidationMessage('Campo obligatorio');
        return value;
      }
    });

    if (!nombre) return;

    // 2. Telefono
    const { value: telefono } = await alertaNinjaFire({
      title: 'VERIFICACION',
      input: 'text',
      inputLabel: 'Numero de WhatsApp',
      inputPlaceholder: 'Ej: 3001234567',
      showCancelButton: true,
      confirmButtonText: 'ENVIAR CODIGO',
      preConfirm: (value) => {
        if (!value || value.trim() === '') Swal.showValidationMessage('Numero invalido');
        return value;
      }
    });

    if (!telefono) return;

    let telefonoFormateado = telefono.trim();
    if (!telefonoFormateado.startsWith("+57")) telefonoFormateado = "+57" + telefonoFormateado;

    // 3. Enviar Token
    const res = await fetch("/enviar_token_recuperacion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telefono: telefonoFormateado })
    });
    const dataStatus = await res.json();
    if (!dataStatus.success) return alertaNinja("error", "FALLIDO", dataStatus.msg);

    await alertaNinja("success", "CODIGO ENVIADO", "Revisa tu WhatsApp.");

    // 4. Validar Codigo
    const { value: token } = await alertaNinjaFire({
      title: 'VALIDAR CODIGO',
      input: 'text',
      inputLabel: 'Codigo de 6 digitos',
      inputPlaceholder: '123456',
      showCancelButton: true,
      confirmButtonText: 'VALIDAR',
      preConfirm: (value) => {
        if (!value || value.trim().length < 4) Swal.showValidationMessage('Codigo corto');
        return value;
      }
    });

    if (!token) return;

    // 5. Nueva Clave
    const { value: nuevaContrasena } = await alertaNinjaFire({
      title: 'NUEVA CLAVE',
      input: 'password',
      inputLabel: 'Minimo 6 caracteres',
      inputPlaceholder: '********',
      showCancelButton: true,
      confirmButtonText: 'ACTUALIZAR',
      preConfirm: (value) => {
        if (!value || value.length < 6) Swal.showValidationMessage('Clave muy corta');
        return value;
      }
    });

    if (!nuevaContrasena) return;

    // 6. Confirmar Final
    const respFinal = await fetch("/Em_validar_token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, telefono, token, nueva_clave: nuevaContrasena })
    });
    const finalResult = await respFinal.json();

    if (finalResult.success) {
      alertaNinja("success", "SHINOBI", "Contrasena actualizada con exito!");
    } else {
      alertaNinja("error", "ERROR", finalResult.msg);
    }

  } catch (err) {
    console.error("Error en flujo de recuperacion:", err);
    alertaNinja("error", "CRITICO", "No se pudo completar el proceso.");
  }
};
