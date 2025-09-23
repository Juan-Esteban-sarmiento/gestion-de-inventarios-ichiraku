document.getElementById("buscarProducto").addEventListener("input", async function() {
  let termino = this.value.trim();
  let resultBox = document.getElementById("resultProducto");

  if (termino.length === 0) {
    resultBox.innerHTML = "<p>No se ha realizado ninguna búsqueda</p>";
    return;
  }

  try {
    const response = await fetch("/buscar_producto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ termino })
    });

    const data = await response.json();

    if (data.success) {
      resultBox.innerHTML = data.productos.map(prod => `
        <div class="producto-card">
          <div style="display: flex; align-items: center; gap: 15px;">
            <img src="${prod.Foto ? prod.Foto : '/static/image/default.png'}" 
              alt="Foto de ${prod.Nombre}" 
              style="width:60px; height:60px; border-radius:50%; object-fit:cover;">
            <div class="producto-info">
              <p><strong>${prod.Nombre}</strong></p>
              <p>ID: ${prod.Id_Producto}</p>
              <p>Categoria: ${prod.Categoria}</p>
              <p>Unidad: ${prod.Unidad}</p>
            </div>
          </div>
        </div>
      `).join("");
        resultBox.innerHTML = data.productos.map(prod => `
          <div class="producto-card">
            <div style="display: flex; align-items: center; gap: 15px;">
              <img src="${prod.Foto ? prod.Foto : '/static/image/default.png'}" 
                alt="Foto de ${prod.Nombre}" 
                style="width:60px; height:60px; border-radius:50%; object-fit:cover;">
              <div class="producto-info">
                <p><strong>${prod.Nombre}</strong></p>
                <p>ID: ${prod.Id_Producto}</p>
                <p>Categoria: ${prod.Categoria}</p>
                <p>Unidad: ${prod.Unidad}</p>
              </div>
              <div class="producto-actions">
                <button onclick="eliminarProducto('${prod.Id_Producto}')">Eliminar</button>
              </div>
            </div>
          </div>
        `).join("");
    } else {
      resultBox.innerHTML = "<p>" + data.msg + "</p>";
    }

  } catch (err) {
    console.error("Error en la búsqueda de producto:", err);
    resultBox.innerHTML = "<p>Error en el servidor</p>";
  }
});
