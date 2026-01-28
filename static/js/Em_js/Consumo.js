document.addEventListener('DOMContentLoaded', () => {
    buscarProductos();
});

let carritoConsumo = [];

document.getElementById("searchTerm").addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
        e.preventDefault();
        buscarProductos();
    }
});

async function buscarProductos() {
    const term = document.getElementById("searchTerm").value.trim();
    const container = document.getElementById("productos-container");

    try {
        const response = await fetch("/buscar_producto", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ termino: term })
        });

        const data = await response.json();

        if (data.success && data.productos) {
            container.innerHTML = data.productos.map(prod => `
        <div class="producto-card" onclick="agregarAlConsumo('${prod.id_producto}', '${prod.nombre}', '${prod.unidad}')">
            <div style="display:flex; align-items:center; gap:10px;">
                <img src="${prod.foto || '/static/image/default.png'}" style="width:50px; height:50px; border-radius:50%; object-fit:cover;">
                <div>
                    <h4 style="margin:0; color:#fff;">${prod.nombre}</h4>
                    <small style="color:#aaa;">${prod.categoria} (${prod.unidad})</small>
                </div>
            </div>
            <button class="add-btn">+</button>
        </div>
      `).join("");
        } else {
            container.innerHTML = "<p>No se encontraron productos.</p>";
        }
    } catch (err) {
        console.error(err);
        container.innerHTML = "<p>Error al cargar productos.</p>";
    }
}

function agregarAlConsumo(id, nombre, unidad) {
    const existente = carritoConsumo.find(item => item.id === id);
    if (existente) {
        existente.cantidad++;
    } else {
        carritoConsumo.push({ id, nombre, unidad, cantidad: 1 });
    }
    renderizarConsumo();
}

function renderizarConsumo() {
    const lista = document.getElementById("consumo-lista");
    lista.innerHTML = "";

    carritoConsumo.forEach((item, index) => {
        const li = document.createElement("li");
        li.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
        <span>${item.nombre}</span>
        <div style="display:flex; align-items:center; gap:5px;">
          <input type="number" min="1" value="${item.cantidad}" onchange="actualizarCantidad(${index}, this.value)" style="width:60px;">
          <span>${item.unidad}</span>
          <button onclick="eliminarDelConsumo(${index})" style="background:#ff3333; border:none; color:white; cursor:pointer;">X</button>
        </div>
      </div>
    `;
        lista.appendChild(li);
    });
}

function actualizarCantidad(index, valor) {
    const val = parseInt(valor);
    if (val > 0) {
        carritoConsumo[index].cantidad = val;
    }
}

function eliminarDelConsumo(index) {
    carritoConsumo.splice(index, 1);
    renderizarConsumo();
}

async function confirmarConsumo() {
    if (carritoConsumo.length === 0) {
        alertaNinja("warning", "VACIO", "No has seleccionado productos para consumir.");
        return;
    }

    Swal.fire({
        title: '<span style="font-family:njnaruto;">REGISTRAR GASTO</span>',
        text: "Se descontará del inventario de tu sucursal.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#e60000',
        confirmButtonText: 'REGISTRAR'
    }).then(async (result) => {
        if (result.isConfirmed) {
            // Enviar uno por uno o en lote. El backend actual soporta uno por uno.
            // Vamos a enviar uno por uno para simplificar por ahora.

            let errores = 0;

            for (const item of carritoConsumo) {
                try {
                    const res = await fetch("/registrar_consumo", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            id_producto: item.id,
                            cantidad: item.cantidad
                        })
                    });
                    const data = await res.json();
                    if (!data.success) {
                        errores++;
                        alertaNinja("error", `Error con ${item.nombre}`, data.msg);
                    }
                } catch (e) {
                    errores++;
                }
            }

            if (errores === 0) {
                alertaNinja("success", "EXITO", "Consumo registrado correctamente.");
                carritoConsumo = [];
                renderizarConsumo();
            } else {
                alertaNinja("warning", "AVISO", `Se registraron algunos productos, pero hubo ${errores} errores.`);
            }
        }
    });
}
