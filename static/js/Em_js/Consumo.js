/* ============================================
   CONSUMO.JS - Registro de Consumo Diario
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    buscarProductos();
    cargarHistorialHoy();
});

let carritoConsumo = [];

// Buscar al presionar Enter
document.getElementById("searchTerm").addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
        e.preventDefault();
        buscarProductos();
    }
});

// ─── BUSCAR PRODUCTOS ───
async function buscarProductos() {
    const term = document.getElementById("searchTerm").value.trim();
    const container = document.getElementById("productos-container");

    container.innerHTML = `<div class="loading-spinner"><div class="spinner"></div><p>Cargando productos...</p></div>`;

    try {
        const response = await fetch("/buscar_producto_empleado", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ termino: term })
        });

        const data = await response.json();

        if (data.success && data.productos && data.productos.length > 0) {
            container.innerHTML = data.productos.map(prod => `
                <div class="producto-card" onclick="agregarAlConsumo('${prod.id_producto}', '${prod.nombre.replace(/'/g, "\\'")}', '${prod.unidad}')">
                    <div class="producto-card-img">
                        <img src="${prod.foto || '/static/image/default.png'}" alt="${prod.nombre}"
                             onerror="this.onerror=null; this.src='/static/image/default.png';">
                    </div>
                    <div class="producto-card-info">
                        <h4>${prod.nombre}</h4>
                        <span class="producto-categoria">${prod.categoria || 'Sin categoría'}</span>
                        <span class="producto-unidad">${prod.unidad}</span>
                    </div>
                    <button class="add-btn" title="Agregar al consumo">+</button>
                </div>
            `).join("");
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No se encontraron productos</p>
                </div>`;
        }
    } catch (err) {
        console.error(err);
        container.innerHTML = `
            <div class="empty-state">
                <p>Error al cargar productos</p>
            </div>`;
    }
}

// ─── AGREGAR AL CARRITO DE CONSUMO ───
function agregarAlConsumo(id, nombre, unidad) {
    const existente = carritoConsumo.find(item => item.id === id);
    if (existente) {
        existente.cantidad++;
    } else {
        carritoConsumo.push({ id, nombre, unidad, cantidad: 1 });
    }
    renderizarConsumo();
}

// ─── RENDERIZAR CARRITO DE CONSUMO ───
function renderizarConsumo() {
    const lista = document.getElementById("consumo-lista");
    const badge = document.getElementById("consumo-count");

    if (carritoConsumo.length === 0) {
        lista.innerHTML = `
            <li class="empty-cart">
                <p>Agrega productos para registrar consumo</p>
            </li>`;
        if (badge) badge.textContent = "0";
        return;
    }

    if (badge) badge.textContent = carritoConsumo.length;

    lista.innerHTML = "";
    carritoConsumo.forEach((item, index) => {
        const li = document.createElement("li");
        li.className = "consumo-item";
        li.innerHTML = `
            <div class="consumo-item-info">
                <span class="consumo-item-name">${item.nombre}</span>
                <span class="consumo-item-unidad">${item.unidad}</span>
            </div>
            <div class="consumo-item-controls">
                <button class="qty-btn minus" onclick="event.stopPropagation(); cambiarCantidad(${index}, -1)">−</button>
                <input type="number" min="1" value="${item.cantidad}"
                       onchange="actualizarCantidad(${index}, this.value)"
                       class="qty-input">
                <button class="qty-btn plus" onclick="event.stopPropagation(); cambiarCantidad(${index}, 1)">+</button>
                <button class="remove-btn" onclick="event.stopPropagation(); eliminarDelConsumo(${index})" title="Eliminar">✕</button>
            </div>
        `;
        lista.appendChild(li);
    });
}

function cambiarCantidad(index, delta) {
    const newVal = carritoConsumo[index].cantidad + delta;
    if (newVal >= 1) {
        carritoConsumo[index].cantidad = newVal;
        renderizarConsumo();
    }
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

// ─── CONFIRMAR CONSUMO ───
async function confirmarConsumo() {
    if (carritoConsumo.length === 0) {
        alertaNinja("warning", "VACÍO", "No has seleccionado productos para consumir.");
        return;
    }

    const resumen = carritoConsumo.map(i => `• ${i.nombre}: ${i.cantidad} ${i.unidad}`).join("<br>");

    Swal.fire({
        title: '<span style="font-family:njnaruto;">REGISTRAR GASTO</span>',
        html: `<p style="color:#aaa; margin-bottom:15px;">Se descontará del inventario de tu sucursal:</p>
               <div style="text-align:left; color:#ff6b6b; font-size:14px; line-height:1.8;">${resumen}</div>`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#e60000',
        cancelButtonColor: '#333',
        confirmButtonText: 'REGISTRAR',
        cancelButtonText: 'Cancelar',
        background: '#1a1a2e',
        color: '#fff'
    }).then(async (result) => {
        if (result.isConfirmed) {
            let errores = 0;
            let mensajesError = [];

            // Mostrar loading
            Swal.fire({
                title: 'Registrando...',
                text: 'Descontando del inventario',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); },
                background: '#1a1a2e',
                color: '#fff'
            });

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
                        mensajesError.push(`${item.nombre}: ${data.msg}`);
                    }
                } catch (e) {
                    errores++;
                    mensajesError.push(`${item.nombre}: Error de conexión`);
                }
            }

            Swal.close();

            if (errores === 0) {
                alertaNinja("success", "ÉXITO", "Consumo registrado correctamente.");
                carritoConsumo = [];
                renderizarConsumo();
                cargarHistorialHoy();
            } else if (errores < carritoConsumo.length) {
                alertaNinja("warning", "PARCIAL", `Algunos productos tuvieron errores:\n${mensajesError.join('\n')}`);
                carritoConsumo = [];
                renderizarConsumo();
                cargarHistorialHoy();
            } else {
                alertaNinja("error", "ERROR", `No se pudo registrar:\n${mensajesError.join('\n')}`);
            }
        }
    });
}

// ─── HISTORIAL DEL DÍA ───
async function cargarHistorialHoy() {
    const tbody = document.getElementById("historial-tbody");
    const emptyMsg = document.getElementById("historial-empty");

    if (!tbody) return;

    try {
        const res = await fetch("/historial_consumo_hoy");
        const data = await res.json();

        if (data.success && data.consumos && data.consumos.length > 0) {
            if (emptyMsg) emptyMsg.style.display = "none";
            tbody.style.display = "";

            tbody.innerHTML = data.consumos.map(c => {
                // Formatear hora
                const fecha = new Date(c.fecha);
                const hora = fecha.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });

                return `
                    <tr>
                        <td>${hora}</td>
                        <td>${c.nombre_producto || 'N/A'}</td>
                        <td class="text-center">${c.cantidad}</td>
                        <td>${c.unidad || ''}</td>
                        <td>${c.nombre_empleado || 'N/A'}</td>
                    </tr>
                `;
            }).join("");
        } else {
            tbody.style.display = "none";
            if (emptyMsg) emptyMsg.style.display = "flex";
        }
    } catch (err) {
        console.error("Error cargando historial:", err);
        tbody.style.display = "none";
        if (emptyMsg) emptyMsg.style.display = "flex";
    }
}
