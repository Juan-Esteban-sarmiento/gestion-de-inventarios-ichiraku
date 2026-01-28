// ✅ Registro de producto con alerta ninja
document.getElementById('registerProductForm').addEventListener('submit', async function (e) {
  e.preventDefault();

  const nombre = document.getElementById('nombreProducto').value.trim();
  const categoria = document.getElementById('categoriaProducto').value.trim();
  const unidad = document.getElementById('unidadProducto').value.trim();
  const serial = document.getElementById('serialProducto').value.trim();
  const fotoFile = document.getElementById('fotoProducto').files[0];

  if (!nombre || !categoria || !unidad || !serial) {
    alertaNinja('warning', 'Campos incompletos', 'Debes llenar todos los campos antes de registrar el producto');
    return;
  }
  const nombreRegex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ ()\-'/&.,%+]+$/;
  if (nombre.length < 2 || nombre.length > 100) {
    alertaNinja('warning', 'NOMBRE INVALIDO', 'Debe tener entre 2 y 100 caracteres');
    return;
  }
  if (/\s{2,}/.test(nombre)) {
    alertaNinja('warning', 'NOMBRE INVALIDO', 'No debe incluir espacios dobles');
    return;
  }
  if (/\d/.test(nombre)) {
    alertaNinja('warning', 'NOMBRE INVALIDO', 'El nombre no debe contener números ni cantidades');
    return;
  }
  if (!nombreRegex.test(nombre)) {
    alertaNinja('warning', 'NOMBRE INVALIDO', 'Contiene caracteres no permitidos');
    return;
  }
  const nombreNormalizado = nombre.replace(/\s+/g, ' ').trim().split(' ').map((w, i, arr) => { const lw = w.toLowerCase(); const small = ['de', 'del', 'la', 'el', 'y', 'o', 'en', 'con', 'para', 'por', 'a', 'al', 'un', 'una', 'los', 'las', 'sus']; return (small.includes(lw) && i > 0 && i < arr.length - 1) ? lw : lw.charAt(0).toUpperCase() + lw.slice(1) }).join(' ');

  const formData = new FormData();
  formData.append("nombre", nombreNormalizado);
  formData.append("categoria", categoria);
  formData.append("unidad", unidad);
  formData.append("serial", serial);
  if (fotoFile) formData.append("foto", fotoFile);

  try {
    const response = await fetch('/registrar_producto', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (data.success) {
      alertaNinja('success', 'EXITO', 'Producto registrado correctamente.');
      document.getElementById('registerProductForm').reset();
      document.getElementById('previewFotoProducto').style.display = "none";
      await cargarProductos(); // Recarga dinámica en lugar de forzar reload tosco
    } else {
      alertaNinja('error', 'Error en registro', data.msg);
    }

  } catch (error) {
    alertaNinja('error', 'Error de conexión', 'No se pudo conectar con el servidor.');
  }
});

const categoriasUnidades = {
  "Carnes": ["kg", "g"],
  "Bebidas": ["L", "ml"],
  "Verduras": ["kg", "g"],
  "Frutas": ["kg", "g"],
  "Cereales": ["kg", "g"],
  "Salsas y condimentos": ["ml", "L"],
  "Panes y masas": ["unidad", "docena"],
  "Mariscos": ["kg", "g"],
  "Lacteos": ["L", "ml"],
};

function cargarCategorias() {
  const categoriaSelect = document.getElementById("categoriaProducto");
  categoriaSelect.innerHTML = `<option value="">Seleccione una categoria</option>`;

  Object.keys(categoriasUnidades).forEach(cat => {
    const option = document.createElement("option");
    option.value = cat;
    option.textContent = cat;
    categoriaSelect.appendChild(option);
  });
}

document.getElementById("categoriaProducto").addEventListener("change", function () {
  const categoria = this.value;
  const unidadSelect = document.getElementById("unidadProducto");

  unidadSelect.innerHTML = "";
  unidadSelect.disabled = false;

  if (categoria && categoriasUnidades[categoria]) {
    categoriasUnidades[categoria].forEach(u => {
      const opt = document.createElement("option");
      opt.value = u;
      opt.textContent = u;
      unidadSelect.appendChild(opt);
    });
  } else {
    unidadSelect.innerHTML = `<option value="">Seleccione una categoria primero</option>`;
    unidadSelect.disabled = true;
  }
});

async function cargarProximoID() {
  try {
    const response = await fetch("/obtener_proximo_id")
    const data = await response.json();
    if (data.success) {
      document.getElementById("serialProducto").value = data.proximo_id;
    }
  } catch (error) { console.error(error); }
}

function mostrarProductos(productos) {
  const resultBox = document.getElementById("resultProducto");
  if (!productos || productos.length === 0) {
    resultBox.innerHTML = "<p style='text-align:center; padding:20px; color:#666;'>No hay productos registrados.</p>";
    return;
  }

  resultBox.innerHTML = productos.map(prod => `
    <div class="producto-card" style="${!prod.habilitado ? 'opacity: 0.5;' : ''}">
        <img src="${prod.foto || '/static/image/default.png'}" alt="Foto">
        <div class="producto-info">
          <h4>${prod.nombre}</h4>
          <p>ID: ${prod.id_producto} | ${prod.categoria} (${prod.unidad})</p>
        </div>
        <div class="producto-actions">
          <button onclick="editarProducto('${prod.id_producto}', '${prod.nombre}', '${prod.categoria}', '${prod.unidad}')">Editar</button>
          <button onclick="${prod.habilitado ? `deshabilitarProducto('${prod.id_producto}')` : `habilitarProducto('${prod.id_producto}')`}">${prod.habilitado ? 'Desactivar' : 'Activar'}</button>
        </div>
    </div>
  `).join("");
}

// ✏️ Editar producto (Usa alertaNinjaFire para mantener el estilo Premium)
function editarProducto(id_producto, nombre, categoria, unidad) {
  alertaNinjaFire({
    title: 'Editar Producto',
    html: `
      <input id="editNombre" class="swal2-input ninja-swal-input" placeholder="Nombre" value="${nombre}">
      <input id="editCategoria" class="swal2-input ninja-swal-input" placeholder="Categoria" value="${categoria}">
      <input id="editUnidad" class="swal2-input ninja-swal-input" placeholder="Unidad" value="${unidad}">
      <label style="display:block; margin-top:15px; color:#aaa; font-size:11px; text-transform:uppercase;">Cambiar foto (opcional)</label>
      <input type="file" id="editFoto" class="swal2-file ninja-swal-input" accept="image/*">
    `,
    showCancelButton: true,
    confirmButtonText: 'GUARDAR CAMBIOS',
    cancelButtonText: 'VOLVER',
    preConfirm: () => {
      const n = document.getElementById("editNombre").value.trim();
      const c = document.getElementById("editCategoria").value.trim();
      const u = document.getElementById("editUnidad").value.trim();
      const f = document.getElementById("editFoto").files[0];

      if (!n || !c || !u) { Swal.showValidationMessage('Todos los campos son obligatorios'); return false; }
      return { nombre: n, categoria: c, unidad: u, foto: f };
    }
  }).then(async (result) => {
    if (result.isConfirmed) {
      const data = result.value;
      const formData = new FormData();
      formData.append("nombre", data.nombre);
      formData.append("categoria", data.categoria);
      formData.append("unidad", data.unidad);
      if (data.foto) formData.append("foto", data.foto);

      try {
        const response = await fetch(`/editar_producto/${id_producto}`, {
          method: "POST",
          body: formData
        });
        const res = await response.json();
        if (res.success) {
          alertaNinja('success', 'ACTUALIZADO', 'Producto guardado correctamente.');
          await cargarProductos();
        } else { alertaNinja('error', 'Error', res.msg); }
      } catch (e) { alertaNinja('error', 'Fallo', 'No se pudo conectar.'); }
    }
  });
}

// 📸 Vista previa de la foto
document.getElementById('fotoProducto').addEventListener('change', function (event) {
  const file = event.target.files[0];
  const preview = document.getElementById('previewFotoProducto');
  if (file) {
    const reader = new FileReader();
    reader.onload = (e) => { preview.src = e.target.result; preview.style.display = 'block'; };
    reader.readAsDataURL(file);
  }
});

async function cargarProductos() {
  try {
    const response = await fetch("/buscar_producto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ termino: "" })
    });
    const data = await response.json();
    if (data.success) mostrarProductos(data.productos);
  } catch (err) { console.error(err); }
}

document.getElementById("buscarProducto").addEventListener("keydown", async function (e) {
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
      mostrarProductos(data.productos || []);
    } catch (err) { console.error(err); }
  }
});

// ❌ Deshabilitar
async function deshabilitarProducto(id_producto) {
  const res = await alertaNinjaFire({
    icon: 'warning',
    title: 'DESACTIVAR',
    text: 'El producto no aparecera en el inventario activo.',
    showCancelButton: true,
    confirmButtonText: 'DESACTIVAR',
    cancelButtonText: 'VOLVER'
  });

  if (res.isConfirmed) {
    const response = await fetch(`/cambiar_estado_producto/${id_producto}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habilitado: false })
    });
    const data = await response.json();
    if (data.success) {
      alertaNinja('success', 'DESACTIVADO', 'Estado cambiado correctamente.');
      await cargarProductos();
    }
  }
}

// ✅ Habilitar
async function habilitarProducto(id_producto) {
  const res = await alertaNinjaFire({
    icon: 'question',
    title: 'ACTIVAR',
    text: 'El producto volvera a estar disponible para el inventario.',
    showCancelButton: true,
    confirmButtonText: 'ACTIVAR',
    cancelButtonText: 'VOLVER'
  });

  if (res.isConfirmed) {
    const response = await fetch(`/cambiar_estado_producto/${id_producto}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habilitado: true })
    });
    const data = await response.json();
    if (data.success) {
      alertaNinja('success', 'ACTIVADO', 'Estado cambiado correctamente.');
      await cargarProductos();
    }
  }
}

window.addEventListener("DOMContentLoaded", () => {
  cargarProductos();
  cargarProximoID();
  cargarCategorias();
});
