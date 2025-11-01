// 🎴 ALERTA NINJA CON PALETA NEGRO BLANCO Y ROJO
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
        btn.style.border = '2px solid #ff0000ff';
        btn.style.borderRadius = '8px';
        btn.style.padding = '8px 16px';
        btn.style.transition = '0.3s';
        btn.addEventListener('mouseenter', () => (btn.style.background = '#ff0000ff'));
        btn.addEventListener('mouseleave', () => (btn.style.background = '#ff0000ff'));
      }
    }
  });
}

// 🔄 Evita errores al recargar desde cache
window.addEventListener('pageshow', function (event) {
  if (event.persisted) window.location.reload();
});

// 🧾 Registro de empleado
document.getElementById('registerForm').addEventListener('submit', async function (e) {
  e.preventDefault();

  const formData = new FormData();
  formData.append("nombre", document.getElementById('nombre').value);
  formData.append("cedula", document.getElementById('cedula').value);
  formData.append("contrasena", document.getElementById('contrasena').value);
  formData.append("contacto", document.getElementById('contacto').value);

  const fotoFile = document.getElementById('foto').files[0];
  if (fotoFile) formData.append("foto", fotoFile);

  try {
    const response = await fetch('/registrar_empleado', { method: 'POST', body: formData });
    const data = await response.json();

    if (data.success) {
      alertaNinja('success', 'Registrado correctamente', data.msg || 'Empleado agregado exitosamente');
      document.getElementById('registerForm').reset();
      setTimeout(() => window.location.reload(), 1000);
    } else {
      alertaNinja('error', 'Error en registro', data.msg || 'No se pudo registrar el empleado');
    }
  } catch (error) {
    alertaNinja('error', 'Error del servidor', 'Ocurrio un problema al registrar el empleado');
  }
});

// 📸 Vista previa de la foto
document.getElementById('foto').addEventListener('change', function () {
  const file = this.files[0];
  const preview = document.getElementById('previewFoto');

  if (file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      preview.src = e.target.result;
      preview.style.display = "block";
      alertaNinja('info', 'Foto seleccionada', 'La imagen se ha cargado correctamente');
    };
    reader.readAsDataURL(file);
  } else {
    preview.src = "";
    preview.style.display = "none";
    alertaNinja('warning', 'Foto eliminada', 'No hay imagen seleccionada');
  }
});

document.addEventListener("DOMContentLoaded", async function () {
  await cargarEmpleados("");
});

document.getElementById("buscarEmpleado").addEventListener("keydown", async function (e) {
  if (e.key === "Enter") {
    e.preventDefault();
    const termino = this.value.trim();
    await cargarEmpleados(termino);
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
        <div class="empleado-card" style="${!emp.habilitado ? 'opacity: 0.6; background-color: #f8d7d710;' : ''}">
          <div style="display: flex; align-items: center; gap: 15px;">
            <img src="${emp.foto || '/static/image/default.png'}" alt="Foto de ${emp.nombre}" style="width:60px; height:60px; border-radius:50%; object-fit:cover;">
            <div class="empleado-info">
              <p><strong>${emp.nombre || 'Sin nombre'}</strong></p>
              <p>ID ${emp.cedula || '---'}</p>
              <p>Contacto ${emp.numero_contacto || '---'}</p>
            </div>
          </div>
          <div class="empleado-actions">
            <button onclick="editarEmpleado('${emp.cedula}', '${emp.nombre}', '${emp.numero_contacto}', '${emp.contrasena || ''}')">Editar</button>
            <button onclick="${emp.habilitado ? `desabilitarEmpleado('${emp.cedula}')` : `habilitarEmpleado('${emp.cedula}')`}">${emp.habilitado ? 'Deshabilitar' : 'Habilitar'}</button>
          </div>
        </div>
      `).join("");
    } else {
      resultBox.innerHTML = "<p>No se encontraron empleados</p>";
    }

  } catch (err) {
    console.error("Error en la busqueda", err);
    resultBox.innerHTML = "<p>Error en el servidor</p>";
  }
}

// ✏️ Editar empleado
function editarEmpleado(cedula, nombre, contacto, contrasena) {
  Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Editar empleado</span>',
    html: `
      <input id="editNombre" class="swal2-input" placeholder="Nombre" value="${nombre}">
      <input id="editCedula" class="swal2-input" placeholder="Cedula" value="${cedula}">
      <input id="editContacto" class="swal2-input" placeholder="Numero de contacto" value="${contacto}">
    `,
    confirmButtonText: '<span style="font-family:njnaruto;">Guardar</span>',
    showCancelButton: true,
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000',
    color: '#fff',
    confirmButtonColor: '#ff0000ff',
    cancelButtonColor: '#ff0000ff',
    preConfirm: () => {
      return {
        nombre: document.getElementById("editNombre").value,
        cedula: document.getElementById("editCedula").value,
        numero_contacto: document.getElementById("editContacto").value,
      };
    }
  }).then(async (result) => {
    if (result.isConfirmed) {
      const data = result.value;
      const response = await fetch(`/editar_empleado/${cedula}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
      const resData = await response.json();
      if (resData.success) {
        alertaNinja('success', 'Empleado actualizado', resData.msg);
        await cargarEmpleados("");
      } else {
        alertaNinja('error', 'Error al actualizar', resData.msg);
      }
    }
  });
}

// ❌ Deshabilitar empleado
async function desabilitarEmpleado(cedula) {
  const confirmacion = await Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Deshabilitar empleado</span>',
    text: "El empleado se desabilitara",
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#ff0000ff',
    cancelButtonColor: '#ff0000ff',
    confirmButtonText: '<span style="font-family:njnaruto;">Si deshabilitar</span>',
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000'
  });

  if (confirmacion.isConfirmed) {
    try {
      const response = await fetch(`/cambiar_estado_empleado/${cedula}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ habilitado: false })
      });
      
      const data = await response.json();
      if (data.success) {
        alertaNinja('success', 'Empleado deshabilitado', data.msg);
        await cargarEmpleados();
      } else {
        alertaNinja('error', 'Error', data.msg);
      }
    } catch (error) {
      console.error("Error al deshabilitar el empleado", error);
      alertaNinja('error', 'Error del servidor', 'No se pudo deshabilitar el empleado');
    }
  }
}

// ✅ Habilitar empleado
async function habilitarEmpleado(cedula) {
  const confirmacion = await Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Habilitar empleado</span>',
    text: "El empleado volvera a estar habilitado",
    icon: 'question',
    showCancelButton: true,
    confirmButtonColor: '#ff0000ff',
    cancelButtonColor: '#ff0000ff',
    confirmButtonText: '<span style="font-family:njnaruto;">Si habilitar</span>',
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000'
  });

  if (confirmacion.isConfirmed) {
    try {
      const response = await fetch(`/cambiar_estado_empleado/${cedula}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ habilitado: true })
      });
      
      const data = await response.json();
      if (data.success) {
        alertaNinja('success', 'Empleado habilitado', data.msg);
        await cargarEmpleados();
      } else {
        alertaNinja('error', 'Error', data.msg);
      }
    } catch (error) {
      console.error("Error al habilitar producto", error);
      alertaNinja('error', 'Error del servidor', 'No se pudo habilitar el producto');
    }
  }
}
