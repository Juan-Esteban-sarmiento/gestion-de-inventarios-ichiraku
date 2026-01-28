// 🔄 Evita errores al recargar desde cache
window.addEventListener('pageshow', function (event) {
  if (event.persisted) window.location.reload();
});

// 🧾 REGISTRO DE LOCAL
document.getElementById('registerForm').addEventListener('submit', async function (e) {
  e.preventDefault();

  const nombre = document.getElementById('nombre_local').value.trim();
  const direccion = document.getElementById('ubicacion').value.trim();
  const id_local = document.getElementById('id_local').value.trim();
  const fotoFile = document.getElementById('foto_local').files[0];

  if (!nombre || !direccion || !id_local) {
    alertaNinja('warning', 'Campos incompletos', 'Debes llenar todos los campos antes de registrar el local.');
    return;
  }

  const formData = new FormData();
  formData.append('nombre', nombre);
  formData.append('direccion', direccion);
  formData.append('id_local', id_local);
  if (fotoFile) formData.append('foto', fotoFile);

  try {
    const response = await fetch('/registrar_local', { method: 'POST', body: formData });
    const data = await response.json();

    if (data.success) {
      alertaNinja('success', '¡Éxito!', 'Punto de venta registrado correctamente.');
      document.getElementById('registerForm').reset();
      document.getElementById('previewFotoLocal').style.display = 'none';
      await cargarLocales(""); // Recarga dinámica suave
      await obtenerSiguienteId(); // Refrescar ID para el próximo registro
    } else {
      alertaNinja('error', 'Error en registro', data.msg);
    }
  } catch (error) {
    alertaNinja('error', 'Error de conexión', 'Ocurrió un problema de red.');
  }
});

// 📸 VISTA PREVIA DE FOTO
document.getElementById('foto_local').addEventListener('change', function () {
  const file = this.files[0];
  const preview = document.getElementById('previewFotoLocal');
  if (file) {
    const reader = new FileReader();
    reader.onload = (e) => { preview.src = e.target.result; preview.style.display = "block"; };
    reader.readAsDataURL(file);
  }
});

// 🔍 BUSCAR LOCALES
document.getElementById('buscarLocal').addEventListener('keydown', async function (e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    await cargarLocales(this.value.trim());
  }
});

async function cargarLocales(termino = "") {
  const resultBox = document.getElementById("resultLocal");
  try {
    const response = await fetch("/buscar_local", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ termino })
    });
    const data = await response.json();
    if (data.success) {
      resultBox.innerHTML = data.locales.map(loc => `
        <div class="local-card" style="${!loc.habilitado ? 'opacity: 0.5;' : ''}">
            <img src="${loc.foto || '/static/image/default.png'}" alt="Foto">
            <div class="local-info">
              <h4>${loc.nombre}</h4>
              <p>ID: ${loc.id_local} | ${loc.direccion}</p>
            </div>
            <div class="local-actions">
              <button onclick="editarLocal('${loc.id_local}', '${loc.nombre}', '${loc.direccion}')">Editar</button>
              <button onclick="${loc.habilitado ? `deshabilitarLocal('${loc.id_local}')` : `habilitarLocal('${loc.id_local}')`}">${loc.habilitado ? 'Desactivar' : 'Activar'}</button>
            </div>
        </div>
      `).join("");
    } else {
      resultBox.innerHTML = `<p style="text-align:center; padding:20px; color:#666;">No hay locales registrados.</p>`;
    }
  } catch (err) { console.error(err); }
}

// ✏️ Editar local (Usa alertaNinjaFire para coherencia)
function editarLocal(id_local, nombre, direccion) {
  alertaNinjaFire({
    title: 'Editar Local',
    html: `
      <input id="editNombre" class="swal2-input ninja-swal-input" placeholder="Nombre" value="${nombre}">
      <input id="editDireccion" class="swal2-input ninja-swal-input" placeholder="Ubicación" value="${direccion}">
    `,
    showCancelButton: true,
    confirmButtonText: 'GUARDAR CAMBIOS',
    cancelButtonText: 'VOLVER',
    preConfirm: () => {
      const n = document.getElementById("editNombre").value.trim();
      const d = document.getElementById("editDireccion").value.trim();
      if (!n || !d) { Swal.showValidationMessage("Todos los campos son obligatorios"); return false; }
      return { nombre: n, direccion: d };
    }
  }).then(async (result) => {
    if (result.isConfirmed) {
      const response = await fetch(`/editar_local/${id_local}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result.value)
      });
      const res = await response.json();
      if (res.success) {
        alertaNinja('success', '¡Actualizado!', 'Datos del punto de venta guardados.');
        await cargarLocales("");
      } else { alertaNinja('error', 'Error', res.msg); }
    }
  });
}

// 🔒 Deshabilitar
async function deshabilitarLocal(id_local) {
  const confirm = await alertaNinjaFire({
    icon: 'warning',
    title: '¿Desactivar Local?',
    text: 'Este punto de venta ya no podrá registrar pedidos.',
    showCancelButton: true,
    confirmButtonText: 'SÍ, DESACTIVAR',
    cancelButtonText: 'CANCELAR'
  });

  if (confirm.isConfirmed) {
    const response = await fetch(`/cambiar_estado_local/${id_local}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habilitado: false })
    });
    const data = await response.json();
    if (data.success) {
      alertaNinja('success', 'Desactivado', 'Estado cambiado correctamente.');
      await cargarLocales();
    }
  }
}

// ✅ Habilitar
async function habilitarLocal(id_local) {
  const confirm = await alertaNinjaFire({
    icon: 'question',
    title: '¿Activar Local?',
    text: 'Habilitarás de nuevo este punto de venta.',
    showCancelButton: true,
    confirmButtonText: 'SÍ, ACTIVAR',
    cancelButtonText: 'CANCELAR'
  });

  if (confirm.isConfirmed) {
    const response = await fetch(`/cambiar_estado_local/${id_local}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habilitado: true })
    });
    const data = await response.json();
    if (data.success) {
      alertaNinja('success', 'Activado', 'Estado cambiado correctamente.');
      await cargarLocales();
    }
  }
}

async function obtenerSiguienteId() {
  try {
    const res = await fetch('/obtener_siguiente_id_local');
    const data = await res.json();
    if (data.success) document.getElementById('id_local').value = data.siguiente_id;
  } catch (err) { console.error(err); }
}

document.addEventListener('DOMContentLoaded', async () => {
  await obtenerSiguienteId();
  await cargarLocales('');
});
