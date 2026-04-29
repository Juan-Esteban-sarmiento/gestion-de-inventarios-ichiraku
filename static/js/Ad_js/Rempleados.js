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

  // Mostrar loading en el boton
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
      alertaNinja('success', 'EXITO', 'Personal registrado correctamente.');
      document.getElementById('registerForm').reset();
      document.getElementById('previewFoto').style.display = 'none';
      await cargarEmpleados("");
    } else {
      alertaNinja('error', 'Error en registro', data.msg);
    }

  } catch (error) {
    alertaNinja('error', 'Error de conexion', 'No se pudo conectar con el servidor.');
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
            <div class="empleado-actions" style="gap: 5px;">
              <button onclick="editarEmpleado('${emp.cedula}', '${emp.nombre}', '${emp.telefono}')">Editar</button>
              <button onclick="${emp.habilitado ? `desabilitarEmpleado('${emp.cedula}')` : `habilitarEmpleado('${emp.cedula}')`}">${emp.habilitado ? 'Desactivar' : 'Activar'}</button>
              <button class="btn-llave" onclick="verLlaveMaestra('${emp.cedula}', '${emp.nombre}')" style="background: #333; color: #ff9800; border: 1px solid #ff9800;">🔑 Ver Llave</button>
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
      <p style="color:#aaa; font-size:13px; margin-top:15px; font-family:'Montserrat', sans-serif;">El telefono (${telefono}) no se puede modificar.</p>
    `,
    showCancelButton: true,
    confirmButtonText: 'GUARDAR CAMBIOS',
    cancelButtonText: 'CANCELAR',
    preConfirm: () => {
      const n = document.getElementById("editNombre").value.trim();
      if (!n) { Swal.showValidationMessage('El nombre es obligatorio'); return false; }
      if (/\d/.test(n)) { Swal.showValidationMessage('El nombre no puede contener numeros'); return false; }
      return { nombre: n };
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
          alertaNinja('success', 'ACTUALIZADO', 'Los datos han sido guardados.');
          await cargarEmpleados("");
        } else { alertaNinja('error', 'Error', res.msg); }
      } catch (e) { alertaNinja('error', 'Error', 'Fallo en la conexion.'); }
    }
  });
}

// ❌ Deshabilitar
async function desabilitarEmpleado(cedula) {
  const res = await alertaNinjaFire({
    icon: 'warning',
    title: 'DESACTIVAR USUARIO',
    text: 'El usuario ya no podra acceder al sistema.',
    showCancelButton: true,
    confirmButtonText: 'DESACTIVAR',
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
      alertaNinja('success', 'DESACTIVADO', 'Estado cambiado correctamente.');
      await cargarEmpleados();
    }
  }
}

// ✅ Habilitar
async function habilitarEmpleado(cedula) {
  const res = await alertaNinjaFire({
    icon: 'question',
    title: 'ACTIVAR USUARIO',
    text: 'El usuario recuperara el acceso al sistema.',
    showCancelButton: true,
    confirmButtonText: 'ACTIVAR',
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
      alertaNinja('success', 'ACTIVADO', 'Estado cambiado correctamente.');
      await cargarEmpleados();
    }
  }
}

// 🔑 VER LLAVE MAESTRA (PARA EL ADMIN)
async function verLlaveMaestra(cedula, nombre) {
  try {
    const response = await fetch(`/admin/get_master_key/${cedula}`);
    const data = await response.json();
    if (data.success) {
      alertaNinjaFire({
        title: '🔑 LLAVE MAESTRA',
        html: `
          <p style="color:#eee;">La llave de recuperacion de <strong style="color:#ff9800; text-transform:uppercase;">${nombre}</strong> es:</p>
          <div style="background: #1a1a1a; color: #ff9800; padding: 15px; border-radius: 8px; font-size: 1.5em; letter-spacing: 3px; font-weight: bold; margin: 15px 0; border: 1px solid #ff9800;">
            ${data.key}
          </div>
          <p style="color:#aaa; font-size: 11px;">Usala para ayudar al empleado si olvida su clave.</p>
        `,
        confirmButtonText: 'ENTENDIDO',
        confirmButtonColor: '#ff9800'
      });
    } else {
      alertaNinja('error', 'Error', data.msg);
    }
  } catch (e) {
    alertaNinja('error', 'Error', 'No se pudo conectar con el servidor.');
  }
}
