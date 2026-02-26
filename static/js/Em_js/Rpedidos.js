let carrito = [];

function showMessage(message, type = "success") {
    alertaNinja(type, type === "success" ? "Exito" : "Error", message);
}

// Nueva funcion para mostrar todos los productos (sin filtro)
function mostrarTodos() {
    document.getElementById("searchTerm").value = ""; // Limpia el input
    buscarProductos(); // Llama a buscar con termino vacio
    showMessage("Mostrando todos los productos.", "success");
}

async function buscarProductos(termino = null) {
    if (termino === null) {
        termino = document.getElementById("searchTerm").value.trim();
    }
    const container = document.getElementById("productos-container");
    container.innerHTML = '<p style="text-align:center; color:#ccc;">Cargando productos...</p>';

    console.log("Buscando productos con termino:", termino);

    try {
        const resp = await fetch("/buscar_producto_empleado", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ termino })
        });
        const data = await resp.json();

        console.log("Respuesta del servidor:", data);

        container.innerHTML = "";

        if (data.success && data.productos && data.productos.length > 0) {
            data.productos.forEach(prod => {
                const card = document.createElement("div");
                card.classList.add("producto-card");

                card.innerHTML = `
                    <div class="producto-card-img">
                        <img src="${prod.foto || '/static/image/default.png'}" alt="${prod.nombre}" onerror="this.src='/static/image/default.png'">
                    </div>
                    <div class="producto-card-info">
                        <h4>${prod.nombre}</h4>
                        <span class="producto-categoria">${prod.categoria}</span>
                        <span class="producto-unidad">${prod.unidad}</span>
                    </div>
                    <div class="consumo-item-controls">
                        <input type="number" min="1" max="500" value="1" id="cantidad-${prod.id_producto}" class="qty-input">
                        <button class="add-btn" onclick="agregarCarrito(${prod.id_producto}, '${prod.nombre.replace(/'/g, "\\'")}', '${prod.categoria.replace(/'/g, "\\'")}', '${prod.unidad.replace(/'/g, "\\'")}')">+</button>
                    </div>
                `;
                container.appendChild(card);
            });
            console.log(`Cargados ${data.productos.length} productos.`);
        } else {
            container.innerHTML = "<p style='text-align:center; color:#ccc; padding: 40px;'>No se encontraron productos.</p>";
            if (termino !== "") showMessage("No hay productos disponibles.", "error");
        }
    } catch (error) {
        console.error("Error al buscar productos:", error);
        container.innerHTML = "<p style='text-align:center; color:red; padding: 40px;'>Error de conexión.</p>";
    }
}

function agregarCarrito(id, nombre, categoria, unidad) {
    const cantidadInput = document.getElementById(`cantidad-${id}`);
    const cantidad = parseInt(cantidadInput.value) || 1;

    if (cantidad <= 0) {
        showMessage("Cantidad mínima: 1", "error");
        return;
    }
    if (cantidad > 500) {
        alertaNinja("warning", "CANTIDAD EXCESIVA", "El límite por producto es de 500 unidades para evitar pedidos exorbitantes.");
        return;
    }

    const existingItemIndex = carrito.findIndex(item => item.Id_Producto === id);

    if (existingItemIndex > -1) {
        carrito[existingItemIndex].Cantidad += cantidad;
        showMessage(`+${cantidad} ${nombre}`, "success");
    } else {
        carrito.push({
            Id_Producto: id,
            Nombre: nombre,
            Categoria: categoria,
            Unidad: unidad,
            Cantidad: cantidad
        });
        showMessage(`Agregado: ${nombre}`, "success");
    }

    renderCarrito();
    cantidadInput.value = 1;
}

function renderCarrito() {
    const lista = document.getElementById("pedido-lista");
    const countBadge = document.getElementById("cart-count");
    lista.innerHTML = "";

    if (carrito.length === 0) {
        lista.innerHTML = "<div class='empty-cart'><span class='empty-icon'>🛒</span><p>El carrito está vacío</p></div>";
        countBadge.innerText = "0";
        return;
    }

    let totalItems = 0;
    carrito.forEach((prod, index) => {
        totalItems += prod.Cantidad;
        const li = document.createElement("li");
        li.classList.add("consumo-item");
        li.innerHTML = `
            <div class="consumo-item-info">
                <span class="consumo-item-name">${prod.Nombre}</span>
                <span class="consumo-item-unidad">${prod.Cantidad} ${prod.Unidad} | ${prod.Categoria}</span>
            </div>
            <button class="remove-btn" onclick="eliminarDelCarrito(${index})" title="Eliminar">&times;</button>
        `;
        lista.appendChild(li);
    });

    countBadge.innerText = `${carrito.length}`;
}

function eliminarDelCarrito(index) {
    const removedItem = carrito.splice(index, 1)[0];
    showMessage(`${removedItem.Nombre} eliminado del carrito.`, "success");
    renderCarrito();
}

async function enviarPedido() {
    if (carrito.length === 0) {
        showMessage("El carrito esta vacio. Agrega productos primero.", "error");
        return;
    }

    const id_local = 1;

    const hoy = new Date().toISOString().split("T")[0];
    const caducidad = new Date();
    caducidad.setMonth(caducidad.getMonth() + 1);
    const fechaCaducidad = caducidad.toISOString().split("T")[0];

    const productosParaEnviar = carrito.map(prod => ({
        Id_Producto: prod.Id_Producto,
        Cantidad: prod.Cantidad,
        Fecha_Ingreso: hoy,
        Fecha_Caducidad: fechaCaducidad
    }));

    const body = {
        Id_Local: id_local,
        Productos: productosParaEnviar
    };

    try {
        const resp = await fetch("/registrar_pedido", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });

        const data = await resp.json();

        if (data.success) {
            showMessage("✅ Pedido registrado con exito.", "success");
            carrito = [];
            renderCarrito();
            document.getElementById("searchTerm").value = "";
            buscarProductos();
        } else {
            showMessage(`❌ Error al registrar pedido: ${data.msg}`, "error");
        }
    } catch (error) {
        console.error("Error en la peticion de registro de pedido:", error);
        showMessage("Error de conexion al registrar el pedido. Intentalo de nuevo.", "error");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => {
        buscarProductos("");
    }, 100);
    renderCarrito();
});

document.getElementById("searchTerm").addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        buscarProductos();
    }
});
