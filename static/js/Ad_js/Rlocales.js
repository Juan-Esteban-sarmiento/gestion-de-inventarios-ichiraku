// ⚔️ ALERTA NINJA GLOBAL (colores negro, blanco y rojo)
function alertaNinja(icon, title, text) {
  Swal.fire({
    icon: icon,
    title: `<span style="font-family:njnaruto;">${title}</span>`,
    text: text || '',
    background: '#000',
    color: '#fff',
    confirmButtonColor: '#e60000',
    confirmButtonText: '<span style="font-family:njnaruto;">Aceptar</span>',
    customClass: {
      popup: 'swal2-border-radius',
      title: 'swal2-title-custom',
      confirmButton: 'swal2-confirm-custom'
    }
  });
}

// 🔁 Recarga si se vuelve atrás
window.addEventListener("pageshow", function (event) {
  if (event.persisted) window.location.reload();
});

// 🩸 REGISTRO DE LOCAL
document.getElementById("registerForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const nombre = document.getElementById("nombre_local").value.trim();
  const direccion = document.getElementById("ubicacion").value.trim();
  const id_local = document.getElementById("id_local").value.trim();

  // ⚠️ Validación manual con alerta ninja
  if (!nombre || !direccion || !id_local) {
    alertaNinja('warning', 'Campos incompletos', 'Debes llenar todos los campos antes de registrar el local.');
    return;
  }

  const formData = new FormData();
  formData.append("nombre", nombre);
  formData.append("direccion", direccion);
  formData.append("id_local", id_local);

  try {
    const response = await fetch("/registrar_local", { method: "POST", body: formData });
    const data = await response.json();

    if (data.success) {
      alertaNinja('success', 'Local registrado', data.msg || 'El local fue agregado correctamente.');
      document.getElementById("registerForm").reset();
      setTimeout(() => window.location.reload(), 1000);
    } else {
      alertaNinja('error', 'Error en registro', data.msg || 'No se pudo registrar el local.');
    }
  } catch (err) {
    console.error("❌ Error al registrar local:", err);
    alertaNinja('error', 'Error del servidor', 'Ocurrió un problema al registrar el local.');
  }
});

// 🩸 MOSTRAR LOCALES EN LISTA
function mostrarLocales(locales) {
  const resultBox = document.getElementById("resultLocal");
  if (!locales || locales.length === 0) {
    resultBox.innerHTML = "<p>No se encontraron locales</p>";
    return;
  }

  resultBox.innerHTML = locales.map(loc => `
    <div class="local-card">
      <div class="local-info">
        <p><strong>${loc.nombre}</strong></p>
        <p>ID: ${loc.id_local}</p>
        <p>Dirección: ${loc.direccion}</p>
      </div>
      <div class="local-actions">
        <button onclick="editarLocal(${loc.id_local}, '${loc.nombre}', '${loc.direccion}')">Editar</button>
        <button onclick="eliminarLocal(${loc.id_local})">Eliminar</button>
      </div>
    </div>
  `).join("");
}

// 🩸 CARGAR TODOS LOS LOCALES AL INICIO
async function cargarLocales() {
  try {
    const response = await fetch("/buscar_local", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ termino: "" })
    });

    const data = await response.json();
    if (data.success) mostrarLocales(data.locales);
    else document.getElementById("resultLocal").innerHTML = "<p>No hay locales registrados</p>";
  } catch (err) {
    console.error("Error al cargar locales:", err);
    alertaNinja('error', 'Error del servidor', 'No se pudieron cargar los locales.');
  }
}

// 🩸 BUSCAR SOLO AL PRESIONAR ENTER
document.getElementById("buscarLocal").addEventListener("keydown", async function (e) {
  if (e.key === "Enter") {
    e.preventDefault();
    const termino = this.value.trim();

    try {
      const response = await fetch("/buscar_local", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ termino })
      });

      const data = await response.json();
      if (data.success) mostrarLocales(data.locales);
      else {
        mostrarLocales([]);
        alertaNinja('info', 'Sin resultados', data.msg);
      }
    } catch (err) {
      console.error("Error al buscar local:", err);
      alertaNinja('error', 'Error del servidor', 'Ocurrió un problema en la búsqueda.');
    }
  }
});

// 🩸 EDITAR LOCAL CON SWEETALERT PERSONALIZADO
async function editarLocal(id, nombre, direccion) {
  const { value: formValues } = await Swal.fire({
    title: '<span style="font-family:njnaruto;">Editar Local</span>',
    html: `
      <input id="editNombre" class="swal2-input" placeholder="Nombre" value="${nombre}">
      <input id="editDireccion" class="swal2-input" placeholder="Dirección" value="${direccion}">
    `,
    confirmButtonText: '<span style="font-family:njnaruto;">Guardar</span>',
    showCancelButton: true,
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000',
    color: '#fff',
    confirmButtonColor: '#e60000',
    preConfirm: () => ({
      nombre: document.getElementById("editNombre").value,
      direccion: document.getElementById("editDireccion").value,
    })
  });

  if (!formValues) return;

  try {
    const response = await fetch(`/editar_local/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formValues),
    });

    const resData = await response.json();
    alertaNinja(resData.success ? 'success' : 'error',
      resData.success ? 'Actualizado' : 'Error', resData.msg);
    document.getElementById("buscarLocal").dispatchEvent(new Event("keydown", { key: "Enter" }));
  } catch (err) {
    console.error("❌ Error al editar local:", err);
    alertaNinja('error', 'Error del servidor', 'No se pudo editar el local.');
  }
}

// 🩸 ELIMINAR LOCAL CON CONFIRMACIÓN NINJA
function eliminarLocal(id) {
  Swal.fire({
    title: '<span style="font-family:njnaruto;">¿Eliminar local?</span>',
    html: '<span style="font-family:njnaruto;">Esta acción no se puede deshacer.</span>',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#e60000',
    cancelButtonColor: '#888',
    confirmButtonText: '<span style="font-family:njnaruto;">Eliminar</span>',
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000',
    color: '#fff'
  }).then((result) => {
    if (result.isConfirmed) {
      fetch(`/eliminar_local/${id}`, { method: "DELETE" })
        .then(res => res.json())
        .then(data => {
          alertaNinja(data.success ? 'success' : 'error',
            data.success ? 'Eliminado' : 'Error', data.msg);
          document.getElementById("buscarLocal").dispatchEvent(new Event("keydown", { key: "Enter" }));
        })
        .catch(err => {
          console.error("❌ Error al eliminar local:", err);
          alertaNinja('error', 'Error del servidor', 'No se pudo eliminar el local.');
        });
    }
  });
}

// 🩸 CARGAR LA LISTA AL INICIAR
window.addEventListener("DOMContentLoaded", cargarLocales);
