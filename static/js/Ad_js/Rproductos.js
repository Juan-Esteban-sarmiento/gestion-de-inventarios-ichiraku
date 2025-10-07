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
    <div class="producto-card">
      <div style="display: flex; align-items: center; gap: 15px;">
        <img src="${prod.foto || '/static/image/default.png'}"
             alt="Foto de ${prod.nombre}"
             style="width:60px; height:60px; border-radius:50%; object-fit:cover;">
        <div class="producto-info">
          <p><strong>${prod.nombre}</strong></p>
          <p>ID: ${prod.id_producto}</p>
          <p>Categoría: ${prod.categoria}</p>
          <p>Unidad: ${prod.unidad}</p>
        </div>
      </div>
      <div class="producto-actions">
        <button onclick="editarProducto('${prod.id_producto}', '${prod.nombre}', '${prod.categoria}', '${prod.unidad}')">Editar</button>
        <button onclick="eliminarProducto('${prod.id_producto}')">Eliminar</button>
      </div>
    </div>
  `).join("");
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

// ✅ Ejecutar carga inicial
window.addEventListener("DOMContentLoaded", cargarProductos);
