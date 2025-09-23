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
