// 🔄 Evita errores al recargar desde cache
window.addEventListener('pageshow', function (event) {
  if (event.persisted) window.location.reload();
});

// 🧾 Registro de empleado
// 🧾 Registro de empleado - VERSIÓN MEJORADA CON MANEJO DE ERRORES
// 🧾 Registro de empleado - VERSIÓN FINAL CORREGIDA
document.getElementById('registerForm').addEventListener('submit', async function (e) {
  e.preventDefault();
  
  const nombre = document.getElementById('nombre').value.trim();
  const cedula = document.getElementById('cedula').value.trim();
  const contrasena = document.getElementById('contrasena').value.trim();
  const contacto = document.getElementById('contacto').value.trim();

  // Mostrar loading
  const submitBtn = document.querySelector('#registerForm button[type="submit"]');
  const originalText = submitBtn.innerHTML;
  submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registrando...';
  submitBtn.disabled = true;

  try {
    console.log('🔄 Iniciando validaciones...');

    // Validación de nombre
    const nombreRegex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$/;
    const tieneVocal = /[AEIOUÁÉÍÓÚaeiouáéíóú]/;
    
    if (!nombre) {
      alertaNinja('warning','Campo requerido','El nombre es obligatorio.');
      document.getElementById('nombre').focus();
      return;
    }
    
    if (nombre.length < 2 || nombre.length > 100) {
      alertaNinja('warning','Nombre inválido','El nombre debe tener entre 2 y 100 caracteres.');
      document.getElementById('nombre').focus();
      return;
    }
    
    if (!nombreRegex.test(nombre)) {
      alertaNinja('warning','Nombre inválido','El nombre solo puede contener letras y espacios.');
      document.getElementById('nombre').focus();
      return;
    }
    
    if (!tieneVocal.test(nombre)) {
      alertaNinja('warning','Nombre inválido','El nombre debe contener al menos una vocal.');
      document.getElementById('nombre').focus();
      return;
    }

    // Validación de cédula/ID
    if (!cedula) {
      alertaNinja('warning','Campo requerido','El ID es obligatorio.');
      document.getElementById('cedula').focus();
      return;
    }
    
    if (!/^\d{5,15}$/.test(cedula)) {
      alertaNinja('warning','ID inválido','El ID debe tener entre 5 y 15 dígitos numéricos.');
      document.getElementById('cedula').focus();
      return;
    }

    // Validación de contraseña
    if (!contrasena) {
      alertaNinja('warning','Campo requerido','La contraseña es obligatoria.');
      document.getElementById('contrasena').focus();
      return;
    }
    
    if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,64}$/.test(contrasena)) {
      alertaNinja('warning','Contraseña insegura','Debe tener 8+ caracteres, minúscula, mayúscula, número y símbolo.');
      document.getElementById('contrasena').focus();
      return;
    }

    // Validación de teléfono
    if (!contacto) {
      alertaNinja('warning','Campo requerido','El teléfono es obligatorio.');
      document.getElementById('contacto').focus();
      return;
    }
    
    if (!/^\d{7,15}$/.test(contacto)) {
      alertaNinja('warning','Teléfono inválido','El teléfono debe tener entre 7 y 15 dígitos.');
      document.getElementById('contacto').focus();
      return;
    }

    console.log('✅ Validaciones frontend pasadas, enviando datos...');

    const formData = new FormData();
    formData.append("nombre", nombre);
    formData.append("cedula", cedula);
    formData.append("contrasena", contrasena);
    formData.append("contacto", contacto);

    const fotoFile = document.getElementById('foto').files[0];
    if (fotoFile) {
      formData.append("foto", fotoFile);
    }

    const response = await fetch('/registrar_empleado', { 
      method: 'POST', 
      body: formData 
    });
    
    const data = await response.json();
    console.log('📨 Respuesta del servidor:', data);

    if (data.success) {
      alertaNinja('success', '✅ Registrado correctamente', data.msg);
      // Limpiar formulario
      document.getElementById('registerForm').reset();
      document.getElementById('previewFoto').style.display = 'none';
      // Recargar lista de empleados
      await cargarEmpleados("");
    } else {
      console.log('❌ Error del servidor:', data.msg);
      
      // Manejar diferentes tipos de errores
      if (data.msg.includes("ID") && data.msg.includes("registrado")) {
        alertaNinja('error', '❌ ID duplicado', data.msg);
        document.getElementById('cedula').focus();
        document.getElementById('cedula').select();
      } else if (data.msg.includes("nombre") && data.msg.includes("registrado")) {
        alertaNinja('error', '❌ Nombre duplicado', data.msg);
        document.getElementById('nombre').focus();
        document.getElementById('nombre').select();
      } else if (data.msg.includes("teléfono") && data.msg.includes("registrado")) {
        alertaNinja('error', '❌ Teléfono duplicado', data.msg);
        document.getElementById('contacto').focus();
        document.getElementById('contacto').select();
      } else {
        alertaNinja('error', '❌ Error en registro', data.msg);
      }
    }

  } catch (error) {
    console.error('💥 Error en el registro:', error);
    alertaNinja('error', '❌ Error de conexión', 'No se pudo conectar con el servidor. Verifique su conexión.');
  } finally {
    // Restaurar botón
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
              <p>ID: ${emp.cedula || '---'}</p>
              <p>Contacto: ${emp.telefono || '---'}</p>
            </div>
          </div>
          <div class="empleado-actions">
            <button onclick="editarEmpleado('${emp.cedula}', '${emp.nombre}', '${emp.telefono}', '${emp.contrasena || ''}')">Editar</button>
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

// ✏️ Editar empleado - VERSIÓN CORREGIDA
function editarEmpleado(cedula, nombre, telefono) {
  Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Editar empleado</span>',
    html: `
      <input id="editNombre" class="swal2-input" placeholder="Nombre" value="${nombre || ''}">
      <input id="editCedula" class="swal2-input" placeholder="Cédula" value="${cedula || ''}" disabled>
      <input id="editContacto" class="swal2-input" placeholder="Número de contacto" value="${telefono || ''}">
    `,
    confirmButtonText: '<span style="font-family:njnaruto;">Guardar</span>',
    showCancelButton: true,
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000',
    color: '#fff',
    confirmButtonColor: '#ff0000ff',
    cancelButtonColor: '#ff0000ff',
    preConfirm: () => {
      const nombre = document.getElementById("editNombre").value.trim();
      const telefono = document.getElementById("editContacto").value.trim();
      
      if (!nombre) {
        Swal.showValidationMessage('El nombre es obligatorio');
        return false;
      }
      if (!telefono) {
        Swal.showValidationMessage('El número de contacto es obligatorio');
        return false;
      }
      
      return {
        nombre: nombre,
        telefono: telefono
      };
    }
  }).then(async (result) => {
    if (result.isConfirmed) {
      const data = result.value;
      try {
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
      } catch (error) {
        console.error("Error al editar empleado:", error);
        alertaNinja('error', 'Error del servidor', 'No se pudo actualizar el empleado');
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
