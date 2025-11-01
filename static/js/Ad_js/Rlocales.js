// 🎴 ALERTA NINJA CON PALETA NEGRO, BLANCO Y ROJO
function alertaNinja(icon, title, text) {
  const iconColors = {
    success: '#e60000',
    error: '#ff3333',
    warning: '#ff3333',
    info: '#ffffff',
    question: '#e60000'
  };

  Swal.fire({
    icon: icon,
    title: `<span style="font-family:njnaruto; color:#fff;">${title}</span>`,
    text: text || '',
    background: '#000',
    color: '#fff',
    iconColor: iconColors[icon] || '#e60000',
    confirmButtonColor: '#e60000',
    confirmButtonText: '<span style="font-family:njnaruto;">Aceptar</span>',
    buttonsStyling: false,
    didRender: () => {
      const btn = Swal.getConfirmButton();
      if (btn) {
        btn.style.background = '#e60000';
        btn.style.color = '#fff';
        btn.style.fontWeight = 'bold';
        btn.style.border = '2px solid #ff3333';
        btn.style.borderRadius = '8px';
        btn.style.padding = '8px 16px';
        btn.style.transition = '0.3s';
        btn.addEventListener('mouseenter', () => (btn.style.background = '#ff3333'));
        btn.addEventListener('mouseleave', () => (btn.style.background = '#e60000'));
      }
    }
  });
}

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
      alertaNinja('success', 'Local registrado', data.msg || 'El local fue agregado correctamente.');
      document.getElementById('registerForm').reset();
      document.getElementById('previewFotoLocal').style.display = 'none';
      setTimeout(() => window.location.reload(), 1000);
    } else {
      alertaNinja('error', 'Error en registro', data.msg || 'No se pudo registrar el local.');
    }
  } catch (error) {
    alertaNinja('error', 'Error del servidor', 'Ocurrio un problema al registrar el local.');
  }
});

// 📸 VISTA PREVIA DE FOTO
document.getElementById('foto_local').addEventListener('change', function () {
  const file = this.files[0];
  const preview = document.getElementById('previewFotoLocal');

  if (file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      preview.src = e.target.result;
      preview.style.display = "block";
      preview.style.width = "100px";
      preview.style.height = "100px";
      preview.style.borderRadius = "50%";
      preview.style.objectFit = "cover";
      preview.style.margin = "10px auto";
      preview.style.border = "2px solid #e60000";
      alertaNinja('info', 'Foto seleccionada', 'La imagen se ha cargado correctamente.');
    };
    reader.readAsDataURL(file);
  } else {
    preview.src = "";
    preview.style.display = "none";
    alertaNinja('warning', 'Foto eliminada', 'No hay imagen seleccionada.');
  }
});

// 🔍 BUSCAR LOCALES AL PRESIONAR ENTER
document.getElementById('buscarLocal').addEventListener('keydown', async function (e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    const termino = this.value.trim();
    await cargarLocales(termino);
  }
});

// 📦 Cargar locales
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
        <div class="local-card" style="${!loc.habilitado ? 'opacity: 0.6; background-color: #f8d7d710;' : ''}">
          <div style="display: flex; align-items: center; gap: 15px;">
            <img src="${loc.foto || '/static/image/default.png'}" alt="Foto del local" style="width:60px; height:60px; border-radius:50%; object-fit:cover;">
            <div class="local-info">
              <p><strong>${loc.nombre || 'Sin nombre'}</strong></p>
              <p>ID: ${loc.id_local || '---'}</p>
              <p>Direccion: ${loc.direccion || '---'}</p>
            </div>
          </div>
          <div class="local-actions">
            <button onclick="editarLocal('${loc.id_local}', '${loc.nombre}', '${loc.direccion}')">Editar</button>
            <button onclick="${loc.habilitado ? `deshabilitarLocal('${loc.id_local}')` : `habilitarLocal('${loc.id_local}')`}">${loc.habilitado ? 'Deshabilitar' : 'Habilitar'}</button>
          </div>
        </div>
      `).join("");
    } else {
      resultBox.innerHTML = `<p>No se encontraron locales.</p>`;
    } 
  } catch (err) {
    console.error("Error al cargar locales:", err);
    resultBox.innerHTML = `<p>Error en el servidor.</p>`;
  }
}

// ✏️ Editar local
function editarLocal(id_local, nombre, direccion) {
  Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Editar Local</span>',
    html: `
      <input id="editNombre" class="swal2-input" placeholder="Nombre del local" value="${nombre}">
      <input id="editId" class="swal2-input" placeholder="ID del local" value="${id_local}" disabled>
      <input id="editDireccion" class="swal2-input" placeholder="Direccion" value="${direccion}">
    `,
    confirmButtonText: '<span style="font-family:njnaruto;">Guardar</span>',
    showCancelButton: true,
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000',
    color: '#fff',
    confirmButtonColor: '#e60000',
    cancelButtonColor: '#888',
    preConfirm: () => {
      const nombre = document.getElementById("editNombre").value.trim();
      const direccion = document.getElementById("editDireccion").value.trim();

      if (!nombre || !direccion) {
        Swal.showValidationMessage("Todos los campos son obligatorios");
        return false;
      }

      return { nombre, direccion };
    }
  }).then(async (result) => {
    if (result.isConfirmed) {
      const data = result.value;
      const response = await fetch(`/editar_local/${id_local}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
      const resData = await response.json();

      if (resData.success) {
        alertaNinja('success', 'Local actualizado', resData.msg);
        await cargarLocales("");
      } else {
        alertaNinja('error', 'Error al actualizar', resData.msg);
      }
    }
  });
}

// 🔒 Deshabilitar local
async function deshabilitarLocal(id_local) {
  const confirmacion = await Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Deshabilitar Local?</span>',
    text: "El local se deshabilitara.",
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#ff0000ff',
    cancelButtonColor: '#ff0000ff',
    confirmButtonText: '<span style="font-family:njnaruto;">Si, deshabilitar</span>',
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000'
  });

  if (confirmacion.isConfirmed) {
    try {
      const response = await fetch(`/cambiar_estado_local/${id_local}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ habilitado: false })
      });

      const data = await response.json();

      if (data.success) {
        alertaNinja('success', 'Local deshabilitado', data.msg);
        await cargarLocales();
      } else {
        alertaNinja('error', 'Error', data.msg);
      }
    } catch (error) {
      alertaNinja('error', 'Error del servidor', 'No se pudo deshabilitar el local.');
    }
  }
}

// ✅ Habilitar local
async function habilitarLocal(id_local) {
  const confirmacion = await Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Habilitar Local?</span>',
    text: "El local se habilitara.",
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#ff0000ff',
    cancelButtonColor: '#ff0000ff',
    confirmButtonText: '<span style="font-family:njnaruto;">Si, habilitar</span>',
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000'
  });

  if (confirmacion.isConfirmed) {
    try {
      const response = await fetch(`/cambiar_estado_local/${id_local}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ habilitado: true })
      });

      const data = await response.json();

      if (data.success) {
        alertaNinja('success', 'Local habilitado', data.msg);
        await cargarLocales();
      } else {
        alertaNinja('error', 'Error', data.msg);
      }
    } catch (error) {
      alertaNinja('error', 'Error del servidor', 'No se pudo habilitar el local.');
    }
  }
}

// 🔢 Obtener siguiente ID automaticamente
async function obtenerSiguienteId() {
  try {
    const res = await fetch('/obtener_siguiente_id_local');
    const data = await res.json();

    if (data.success) {
      document.getElementById('id_local').value = data.siguiente_id;
    } else {
      alertaNinja('error', 'Error', 'No se pudo obtener el siguiente ID.');
    }
  } catch (err) {
    alertaNinja('error', 'Error', 'Error al conectar con el servidor.');
  }
}

// Ejecutar al cargar
document.addEventListener('DOMContentLoaded', async function () {
  await obtenerSiguienteId();
  await cargarLocales('');
});
