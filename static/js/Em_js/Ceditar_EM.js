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
    Nombre: formData.get("Nombre")
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

