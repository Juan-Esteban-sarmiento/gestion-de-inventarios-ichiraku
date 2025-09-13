let originalValues = {};

// Guardamos valores iniciales al cargar la página
window.onload = () => {
  document.querySelectorAll("input").forEach(input => {
    originalValues[input.id] = input.value;
  });
};

// Mostrar modal
function mostrarModal(mensaje, tipo="success") {
  const modalText = document.getElementById("modal-text");
  modalText.textContent = mensaje;
  modalText.className = tipo;
  document.getElementById("modal").style.display = "flex";
  document.querySelector(".contenido").classList.add("blur");
}

// Cerrar modal
function cerrarModal() {
  document.getElementById("modal").style.display = "none";
  document.querySelector(".contenido").classList.remove("blur");
}

// Validar cambios antes de enviar
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
    Contrasena: formData.get("Contrasena"),
    Numero_contacto: formData.get("Numero_contacto")
  };

  try {
    let response = await fetch("/Em_Ceditar", {
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
      console.log("JSON recibido:", result);
    } catch (e) {
      console.error("Error al parsear JSON:", e);
      let text = await response.text();
      console.log("📄 Texto crudo:", text);
      return;
    }

    if (result.success) {
      mostrarModal("Usuario actualizado correctamente", result.msg, "success");
    } else {
      mostrarModal("Error al actualizar", result.msg, "error");
    }``
  } catch (err) {
    console.error(" Error en la petición:", err);
  }
});
