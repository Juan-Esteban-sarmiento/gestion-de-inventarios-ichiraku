// 🔄 Evita errores al recargar desde cache
window.addEventListener('pageshow', function (event) {
  if (event.persisted) window.location.reload();
});

// 🧾 Registro de empleado
document.getElementById('registerForm').addEventListener('submit', async function (e) {
  e.preventDefault();

  const nombre = document.getElementById('nombre').value.trim();
  const cedula = document.getElementById('cedula').value.trim();
  const contrasena = document.getElementById('contrasena').value.trim();
  const contacto = document.getElementById('contacto').value.trim();

  // Mostrar loading en el botón
  const submitBtn = document.querySelector('#registerForm button[type="submit"]');
  const originalText = submitBtn.innerHTML;
  submitBtn.innerHTML = 'REGISTRANDO...';
  submitBtn.disabled = true;

  try {
    // Validaciones
    if (!nombre || !cedula || !contrasena || !contacto) {
      alertaNinja('warning', 'Campos incompletos', 'Por favor rellena todos los campos obligatorios.');
      return;
    }

    const formData = new FormData();
    formData.append("nombre", nombre);
    formData.append("cedula", cedula);
    formData.append("contrasena", contrasena);
    formData.append("contacto", contacto);

    const fotoFile = document.getElementById('foto').files[0];
    if (fotoFile) formData.append("foto", fotoFile);

    const response = await fetch('/registrar_empleado', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (data.success) {
      alertaNinja('success', '¡Éxito!', 'Personal registrado correctamente.');
      document.getElementById('registerForm').reset();
      document.getElementById('previewFoto').style.display = 'none';
      await cargarEmpleados("");
    } else {
      alertaNinja('error', 'Error en registro', data.msg);
    }

  } catch (error) {
    alertaNinja('error', 'Error de conexión', 'No se pudo conectar con el servidor.');
  } finally {
    submitBtn.innerHTML = originalText;
    submitBtn.disabled = false;
  }
});

// 📸 Vista previa de la foto
document.getElementById('foto').addEventListener('change', function () {
  const file = this.files[0];
  const preview = document.getElementById('previewFoto');
  if (file) {
    const reader = new FileReader();
    reader.onload = (e) => { preview.src = e.target.result; preview.style.display = "block"; };
    reader.readAsDataURL(file);
  }
});

document.addEventListener("DOMContentLoaded", () => cargarEmpleados(""));

document.getElementById("buscarEmpleado").addEventListener("keydown", async function (e) {
  if (e.key === "Enter") {
    e.preventDefault();
    await cargarEmpleados(this.value.trim());
  }
});

async function cargarEmpleados(termino = "") {
  const resultBox = document.getElementById("resultEmpleado");
  try {
    const response = await fetch("/buscar_empleado", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ termino })
    });
    const data = await response.json();
    if (data.success) {
      resultBox.innerHTML = data.empleados.map(emp => `
        <div class="empleado-card" style="${!emp.habilitado ? 'opacity: 0.5;' : ''}">
            <img src="${emp.foto || '/static/image/default.png'}" alt="Foto">
            <div class="empleado-info">
              <h4>${emp.nombre}</h4>
              <p>ID: ${emp.cedula} | Tel: ${emp.telefono}</p>
            </div>
            <div class="empleado-actions">
              <button onclick="editarEmpleado('${emp.cedula}', '${emp.nombre}', '${emp.telefono}')">Editar</button>
              <button onclick="${emp.habilitado ? `desabilitarEmpleado('${emp.cedula}')` : `habilitarEmpleado('${emp.cedula}')`}">${emp.habilitado ? 'Desactivar' : 'Activar'}</button>
            </div>
        </div>
      `).join("");
    } else {
      resultBox.innerHTML = "<p style='text-align:center; padding:20px; color:#666;'>No se hallaron resultados.</p>";
    }
  } catch (err) { console.error(err); }
}

// ✏️ Editar empleado (Usa alertaNinjaFire para mantener el estilo)
function editarEmpleado(cedula, nombre, telefono) {
  alertaNinjaFire({
    title: 'Editar Personal',
    html: `
      <input id="editNombre" class="swal2-input ninja-swal-input" placeholder="Nombre" value="${nombre}">
      <input id="editContacto" class="swal2-input ninja-swal-input" placeholder="Teléfono" value="${telefono}">
    `,
    showCancelButton: true,
    confirmButtonText: 'GUARDAR CAMBIOS',
    cancelButtonText: 'CANCELAR',
    preConfirm: () => {
      const n = document.getElementById("editNombre").value.trim();
      const t = document.getElementById("editContacto").value.trim();
      if (!n || !t) { Swal.showValidationMessage('Todos los campos son obligatorios'); return false; }
      return { nombre: n, telefono: t };
    }
  }).then(async (result) => {
    if (result.isConfirmed) {
      try {
        const response = await fetch(`/editar_empleado/${cedula}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(result.value)
        });
        const res = await response.json();
        if (res.success) {
          alertaNinja('success', '¡Actualizado!', 'Los datos han sido guardados.');
          await cargarEmpleados("");
        } else { alertaNinja('error', 'Error', res.msg); }
      } catch (e) { alertaNinja('error', 'Error', 'Fallo en la conexión.'); }
    }
  });
}

// ❌ Deshabilitar
async function desabilitarEmpleado(cedula) {
  const res = await alertaNinjaFire({
    icon: 'warning',
    title: '¿Desactivar Empleado?',
    text: 'El usuario ya no podrá acceder al sistema.',
    showCancelButton: true,
    confirmButtonText: 'SÍ, DESACTIVAR',
    cancelButtonText: 'VOLVER'
  });

  if (res.isConfirmed) {
    const response = await fetch(`/cambiar_estado_empleado/${cedula}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habilitado: false })
    });
    const data = await response.json();
    if (data.success) {
      alertaNinja('success', 'Desactivado', 'Estado cambiado correctamente.');
      await cargarEmpleados();
    }
  }
}

// ✅ Habilitar
async function habilitarEmpleado(cedula) {
  const res = await alertaNinjaFire({
    icon: 'question',
    title: '¿Activar Empleado?',
    text: 'El usuario recuperará el acceso al sistema.',
    showCancelButton: true,
    confirmButtonText: 'SÍ, ACTIVAR',
    cancelButtonText: 'VOLVER'
  });

  if (res.isConfirmed) {
    const response = await fetch(`/cambiar_estado_empleado/${cedula}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habilitado: true })
    });
    const data = await response.json();
    if (data.success) {
      alertaNinja('success', 'Activado', 'Estado cambiado correctamente.');
      await cargarEmpleados();
    }
  }
}
