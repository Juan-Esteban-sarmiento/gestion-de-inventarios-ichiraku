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
                card.classList.add("card");

                card.innerHTML = `
                    <img src="${prod.foto || '/static/image/default.png'}" alt="${prod.nombre}" onerror="this.src='/static/image/default.png'">
                    <h3>${prod.nombre}</h3>
                    <p>Categoria: ${prod.categoria}</p>
                    <p>Unidad: ${prod.unidad}</p>
                    <input type="number" min="1" value="1" id="cantidad-${prod.id_producto}">
                    <button onclick="agregarCarrito(${prod.id_producto}, '${prod.nombre.replace(/'/g, "\\'")}', '${prod.categoria.replace(/'/g, "\\'")}', '${prod.unidad.replace(/'/g, "\\'")}')">Agregar al Carrito</button>
                `;
                container.appendChild(card);
            });
            console.log(`Cargados ${data.productos.length} productos.`);
        } else {
            container.innerHTML = "<p style='text-align:center; color:#ccc;'>No se encontraron productos.</p>";
            showMessage("No hay productos disponibles.", "error");
        }
    } catch (error) {
        console.error("Error al buscar productos:", error);
        container.innerHTML = "<p style='text-align:center; color:red;'>Error al cargar productos. Revisa la consola.</p>";
        showMessage("Error de conexion. Intentalo de nuevo.", "error");
    }
}

function agregarCarrito(id, nombre, categoria, unidad) {
    const cantidadInput = document.getElementById(`cantidad-${id}`);
    const cantidad = parseInt(cantidadInput.value) || 1;

    if (cantidad <= 0) {
        showMessage("Cantidad debe ser mayor que 0.", "error");
        return;
    }

    const existingItemIndex = carrito.findIndex(item => item.Id_Producto === id);

    if (existingItemIndex > -1) {
        carrito[existingItemIndex].Cantidad += cantidad;
        showMessage(`Cantidad de ${nombre} actualizada: ${carrito[existingItemIndex].Cantidad}`, "success");
    } else {
        carrito.push({
            Id_Producto: id,
            Nombre: nombre,
            Categoria: categoria,
            Unidad: unidad,
            Cantidad: cantidad
        });
        showMessage(`${nombre} (x${cantidad}) agregado al carrito.`, "success");
    }

    renderCarrito();
    cantidadInput.value = 1;
}

function renderCarrito() {
    const lista = document.getElementById("pedido-lista");
    lista.innerHTML = "";

    if (carrito.length === 0) {
        lista.innerHTML = "<li style='text-align:center; color:#ccc; padding: 20px;'>El carrito esta vacio. Agrega productos.</li>";
        return;
    }

    let totalItems = 0;
    carrito.forEach((prod, index) => {
        totalItems += prod.Cantidad;
        const li = document.createElement("li");
        li.innerHTML = `
            <span>${prod.Nombre} (${prod.Unidad}) - Cantidad: ${prod.Cantidad}</span>
            <button onclick="eliminarDelCarrito(${index})" title="Eliminar">❌</button>
        `;
        lista.appendChild(li);
    });

    const totalLi = document.createElement("li");
    totalLi.innerHTML = `<strong>Total: ${totalItems} items</strong>`;
    totalLi.style.borderTop = "2px solid red";
    totalLi.style.paddingTop = "10px";
    lista.appendChild(totalLi);
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

document.getElementById("searchTerm").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        buscarProductos();
    }
});
