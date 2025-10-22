
// ✅ Alerta Ninja universal
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

// ✅ Registro de producto con alerta ninja
document.getElementById('registerProductForm').addEventListener('submit', async function(e) {
  e.preventDefault();

  const nombre = document.getElementById('nombreProducto').value.trim();
  const categoria = document.getElementById('categoriaProducto').value.trim();
  const unidad = document.getElementById('unidadProducto').value.trim();
  const serial = document.getElementById('serialProducto').value.trim();
  const fotoFile = document.getElementById('fotoProducto').files[0];

  // ⚠️ Validación previa antes de enviar al backend
  if (!nombre || !categoria || !unidad || !serial) {
    alertaNinja('warning', 'Campos incompletos', 'Debes llenar todos los campos antes de registrar el producto.');
    return;
  }

  const formData = new FormData();
  formData.append("nombre", nombre);
  formData.append("categoria", categoria);
  formData.append("unidad", unidad);
  formData.append("serial", serial);
  if (fotoFile) formData.append("foto", fotoFile);

  try {
    const response = await fetch('/registrar_producto', {
      method: 'POST',
      body: formData
    });

    // ⚙️ Convertimos la respuesta a JSON siempre
    const data = await response.json();

    // 🩸 Mostramos cualquier respuesta con alerta ninja
    if (data.success) {
      alertaNinja('success', 'Producto registrado', data.msg || 'El producto se registró correctamente.');
      document.getElementById('registerProductForm').reset();
      document.getElementById('previewFotoProducto').style.display = "none";
      setTimeout(() => window.location.reload(), 1000);
    } else {
      alertaNinja('error', 'Error en registro', data.msg || 'No se pudo registrar el producto.');
    }

  } catch (error) {
    console.error("❌ Error al registrar producto:", error);
    alertaNinja('error', 'Error del servidor', 'Ocurrió un problema al registrar el producto.');
  }
});


// ✅ Mostrar productos con estética ninja
function mostrarProductos(productos) {
  const resultBox = document.getElementById("resultProducto");
  if (!productos || productos.length === 0) {
    resultBox.innerHTML = "<p>No se encontraron productos</p>";
    return;
  }

  resultBox.innerHTML = productos.map(prod => `
    <div class="producto-card" style="${!prod.habilitado ? 'opacity: 0.6; background-color: #f8d7da;' : ''}">
      <div style="display: flex; align-items: center; gap: 15px;">
        <img src="${prod.foto || '/static/image/default.png'}"
             alt="Foto de ${prod.nombre}"
             style="width:60px; height:60px; border-radius:50%; object-fit:cover;">
        <div class="producto-info">
          <p><strong>${prod.nombre}</strong> ${!prod.habilitado ? '<span style="color: #dc3545;">(Deshabilitado)</span>' : ''}</p>
          <p>ID: ${prod.id_producto}</p>
          <p>Categoría: ${prod.categoria}</p>
          <p>Unidad: ${prod.unidad}</p>
        </div>
      </div>
      <div class="producto-actions">
        <button onclick="editarProducto('${prod.id_producto}', '${prod.nombre}', '${prod.categoria}', '${prod.unidad}')">Editar</button>
        ${prod.habilitado ? 
          `<button onclick="deshabilitarProducto('${prod.id_producto}')" style="background-color: #dc3545;">Deshabilitar</button>` :
          `<button onclick="habilitarProducto('${prod.id_producto}')" style="background-color: #28a745;">Habilitar</button>`
        }
      </div>
    </div>
  `).join("");
}
function editarProducto( id_producto,nombre,  categoria, unidad){
  Swal.fire({
      title: '<span style="font-family:njnaruto; color:#fff;">Editar Empleado</span>',
      html: `
        <input id="editNombre" class="swal2-input" placeholder="Nombre" value="${nombre}">
        <input id="editId" class="swal2-input" placeholder="Id delproducto" value="${id_producto}"disabled>
        <input id="editCategoria" class="swal2-input" placeholder="Categoria" value="${categoria}">
        <input id="editUnidad" class="swal2-input" placeholder="Unidad" value="${unidad}">
      `,
      confirmButtonText: '<span style="font-family:njnaruto;">Guardar</span>',
      showCancelButton: true,
      cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
      background: '#000',
      color: '#fff',
      confirmButtonColor: '#e60000',
      cancelButtonColor: '#888',
      preConfirm: () => {
        return {
          nombre: document.getElementById("editNombre").value,
          nueva_id: id_producto,
          categoria: document.getElementById("editCategoria").value,
          unidad: document.getElementById("editUnidad").value
        };
      }
    }).then(async (result) => {
      if (result.isConfirmed) {
        const data = result.value;
      const response = await fetch(`/editar_producto/${id_producto}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
        const resData = await response.json();
        if (resData.success) {
          alertaNinja('success', 'Producto actualizado', resData.msg);
          await cargarEmpleados("");
        } else {
          alertaNinja('error', 'Error al actualizar', resData.msg);
        }
      }
    });
}

// ✅ Cargar productos al inicio
async function cargarProductos() {
  try {
    const response = await fetch("/buscar_producto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ termino: "" })
    });
    const data = await response.json();
    if (data.success) {
      mostrarProductos(data.productos);
    } else {
      document.getElementById("resultProducto").innerHTML = "<p>No hay productos registrados</p>";
    }
  } catch (err) {
    console.error("Error al cargar productos:", err);
    alertaNinja("error", "Error del servidor", "No se pudieron cargar los productos.");
  }
}

// ✅ Buscar solo al presionar Enter
document.getElementById("buscarProducto").addEventListener("keydown", async function(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    const termino = this.value.trim();

    try {
      const response = await fetch("/buscar_producto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ termino })
      });
      const data = await response.json();

      if (data.success) {
        mostrarProductos(data.productos);
      } else {
        mostrarProductos([]);
        alertaNinja("info", "Sin resultados", data.msg);
      }
    } catch (err) {
      console.error("Error en búsqueda:", err);
      alertaNinja("error", "Error del servidor", "Ocurrió un problema en la búsqueda.");
    }
  }
});


// ✅ Deshabilitar producto
async function deshabilitarProducto(id_producto) {
  const confirmacion = await Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">¿Deshabilitar producto?</span>',
    text: "El producto no estará disponible para los empleados.",
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#dc3545',
    cancelButtonColor: '#6c757d',
    confirmButtonText: '<span style="font-family:njnaruto;">Sí, deshabilitar</span>',
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000'
  });

  if (confirmacion.isConfirmed) {
    try {
      const response = await fetch(`/cambiar_estado_producto/${id_producto}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ habilitado: false })
      });
      
      const data = await response.json();
      if (data.success) {
        alertaNinja('success', 'Producto deshabilitado', data.msg);
        await cargarProductos();
      } else {
        alertaNinja('error', 'Error', data.msg);
      }
    } catch (error) {
      console.error("❌ Error al deshabilitar producto:", error);
      alertaNinja('error', 'Error del servidor', 'No se pudo deshabilitar el producto.');
    }
  }
}

// ✅ Habilitar producto
async function habilitarProducto(id_producto) {
  const confirmacion = await Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">¿Habilitar producto?</span>',
    text: "El producto estará disponible para los empleados.",
    icon: 'question',
    showCancelButton: true,
    confirmButtonColor: '#28a745',
    cancelButtonColor: '#6c757d',
    confirmButtonText: '<span style="font-family:njnaruto;">Sí, habilitar</span>',
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000'
  });

  if (confirmacion.isConfirmed) {
    try {
      const response = await fetch(`/cambiar_estado_producto/${id_producto}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ habilitado: true })
      });
      
      const data = await response.json();
      if (data.success) {
        alertaNinja('success', 'Producto habilitado', data.msg);
        await cargarProductos();
      } else {
        alertaNinja('error', 'Error', data.msg);
      }
    } catch (error) {
      console.error("❌ Error al habilitar producto:", error);
      alertaNinja('error', 'Error del servidor', 'No se pudo habilitar el producto.');
    }
  }
}

// ✅ Ejecutar carga inicial
window.addEventListener("DOMContentLoaded", cargarProductos);
