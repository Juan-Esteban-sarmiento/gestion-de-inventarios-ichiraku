// ✅ Registro de producto con alerta ninja
document.getElementById('registerProductForm').addEventListener('submit', async function(e) {
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
    alertaNinja('warning', 'Nombre inválido', 'Debe tener entre 2 y 100 caracteres');
    return;
  }
  if (/\s{2,}/.test(nombre)) {
    alertaNinja('warning', 'Nombre inválido', 'No debe incluir espacios dobles');
    return;
  }
  if (/\d/.test(nombre)) {
    alertaNinja('warning', 'Nombre inválido', 'El nombre no debe contener números ni cantidades');
    return;
  }
  if (!nombreRegex.test(nombre)) {
    alertaNinja('warning', 'Nombre inválido', 'Contiene caracteres no permitidos');
    return;
  }
  const nombreNormalizado = nombre.replace(/\s+/g, ' ').trim().split(' ').map((w,i,arr)=>{const lw=w.toLowerCase();const small=['de','del','la','el','y','o','en','con','para','por','a','al','un','una','los','las','sus'];return (small.includes(lw)&&i>0&&i<arr.length-1)?lw:lw.charAt(0).toUpperCase()+lw.slice(1)}).join(' ');

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
      alertaNinja('success', 'Producto registrado', data.msg || 'El producto se registro correctamente');
      document.getElementById('registerProductForm').reset();
      document.getElementById('previewFotoProducto').style.display = "none";
      setTimeout(() => window.location.reload(), 1000);
    } else {
      alertaNinja('error', 'Error en registro', data.msg || 'No se pudo registrar el producto');
    }

  } catch (error) {
    console.error("Error al registrar producto", error);
    alertaNinja('error', 'Error del servidor', 'Ocurrio un problema al registrar el producto');
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

document.getElementById("categoriaProducto").addEventListener("change", function() {
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
    } else {
      alertaNinja("error", "Error al obtener ID", data.msg);
    }
  } catch (error) {
    console.error("Error al obtener proximo ID", error);
    alertaNinja("error", "Error del servidor", "No se pudo obtener el proximo ID");
  }
}

function mostrarProductos(productos) {
  const resultBox = document.getElementById("resultProducto");
  if (!productos || productos.length === 0) {
    resultBox.innerHTML = "<p>No se encontraron productos</p>";
    return;
  }

  resultBox.innerHTML = productos.map(prod => `
    <div class="producto-card" style="${!prod.habilitado ? 'opacity: 0.6; background-color: #f8d7d710;' : ''}">
      <div style="display: flex; align-items: center; gap: 15px;">
        <img src="${prod.foto || '/static/image/default.png'}"
             alt="Foto de ${prod.nombre}"
             style="width:60px; height:60px; border-radius:50%; object-fit:cover;">
        <div class="producto-info">
          <p>ID ${prod.id_producto}</p>
          <p>Categoria ${prod.categoria}</p>
          <p>Unidad ${prod.unidad}</p>
        </div>
      </div>
      <div class="producto-actions">
        <button onclick="editarProducto('${prod.id_producto}', '${prod.nombre}', '${prod.categoria}', '${prod.unidad}')">Editar</button>
        ${prod.habilitado ? 
          `<button onclick="deshabilitarProducto('${prod.id_producto}')" style="background-color: #ff0000;">Deshabilitar</button>` :
          `<button onclick="habilitarProducto('${prod.id_producto}')" style="background-color: #ff0000;">Habilitar</button>`
        }
      </div>
    </div>
  `).join("");
}

function editarProducto(id_producto, nombre, categoria, unidad) {
  Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Editar Producto</span>',
    html: `
      <input id="editNombre" class="swal2-input" placeholder="Nombre" value="${nombre}">
      <input id="editId" class="swal2-input" placeholder="Id del producto" value="${id_producto}" disabled>
      <input id="editCategoria" class="swal2-input" placeholder="Categoria" value="${categoria}">
      <input id="editUnidad" class="swal2-input" placeholder="Unidad" value="${unidad}">
    `,
    confirmButtonText: '<span style="font-family:njnaruto;">Guardar</span>',
    showCancelButton: true,
    cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
    background: '#000',
    color: '#fff',
    confirmButtonColor: '#e60000',
    cancelButtonColor: '#ff0000ff',
    preConfirm: () => {
      const nombre = document.getElementById("editNombre").value.trim();
      const categoria = document.getElementById("editCategoria").value.trim();
      const unidad = document.getElementById("editUnidad").value.trim();
      const nombreRegex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ ()\-\'\/&.,%+]+$/;
      if (!nombre) { Swal.showValidationMessage('El nombre es obligatorio'); return false; }
      if (nombre.length < 2 || nombre.length > 100) { Swal.showValidationMessage('El nombre debe tener entre 2 y 100 caracteres'); return false; }
      if (/\s{2,}/.test(nombre)) { Swal.showValidationMessage('El nombre no debe tener espacios dobles'); return false; }
      if (/\d/.test(nombre)) { Swal.showValidationMessage('El nombre no debe contener números ni cantidades'); return false; }
      if (!nombreRegex.test(nombre)) { Swal.showValidationMessage('Caracteres no permitidos en el nombre'); return false; }
      if (!categoria || !unidad) { Swal.showValidationMessage('Categoría y unidad son obligatorias'); return false; }
      const nombreNormalizado = nombre.replace(/\s+/g,' ').trim().split(' ').map((w,i,arr)=>{const lw=w.toLowerCase();const small=['de','del','la','el','y','o','en','con','para','por','a','al','un','una','los','las','sus'];return (small.includes(lw)&&i>0&&i<arr.length-1)?lw:lw.charAt(0).toUpperCase()+lw.slice(1)}).join(' ');
      return { nombre: nombreNormalizado, nueva_id: id_producto, categoria, unidad };
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

document.getElementById('fotoProducto').addEventListener('change', function(event) {
  const file = event.target.files[0];
  const preview = document.getElementById('previewFotoProducto');

  if (file) {
    const reader = new FileReader();
    reader.onload = function(e) {
      preview.src = e.target.result;
      preview.style.display = 'block';
    };
    reader.readAsDataURL(file);
  } else {
    preview.src = '';
    preview.style.display = 'none';
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
    if (data.success) {
      mostrarProductos(data.productos);
    } else {
      document.getElementById("resultProducto").innerHTML = "<p>No hay productos registrados</p>";
    }
  } catch (err) {
    console.error("Error al cargar productos", err);
    alertaNinja("error", "Error del servidor", "No se pudieron cargar los productos");
  }
}

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
      console.error("Error en busqueda", err);
      alertaNinja("error", "Error del servidor", "Ocurrio un problema en la busqueda");
    }
  }
});

async function deshabilitarProducto(id_producto) {
  const confirmacion = await Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Deshabilitar producto</span>',
    text: "El producto no estara disponible para los empleados",
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#ff0019ff',
    cancelButtonColor: '#ff0000ff',
    confirmButtonText: '<span style="font-family:njnaruto;">Si deshabilitar</span>',
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
      console.error("Error al deshabilitar producto", error);
      alertaNinja('error', 'Error del servidor', 'No se pudo deshabilitar el producto');
    }
  }
}

async function habilitarProducto(id_producto) {
  const confirmacion = await Swal.fire({
    title: '<span style="font-family:njnaruto; color:#fff;">Habilitar producto</span>',
    text: "El producto estara disponible para los empleados",
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
      console.error("Error al habilitar producto", error);
      alertaNinja('error', 'Error del servidor', 'No se pudo habilitar el producto');
    }
  }
}

window.addEventListener("DOMContentLoaded", () => {
  cargarProductos();
  cargarProximoID();
  cargarCategorias();
});
