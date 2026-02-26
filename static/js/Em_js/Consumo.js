/* ============================================
   CONSUMO.JS - Rediseño Operativo Premium
   ============================================ */

let carritoConsumo = [];

document.addEventListener("DOMContentLoaded", () => {
    buscarProductos();
    cargarHistorialHoy();
    initComparativa();

    // Buscar al presionar Enter
    const searchInput = document.getElementById("searchTerm");
    if (searchInput) {
        searchInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                buscarProductos();
            }
        });
    }
});

// 1. ANALISIS COMPARATIVO (Consumo vs Inventario)
async function initComparativa() {
    try {
        const res = await fetch('/get_consumo_comparative');
        const data = await res.json();

        const tbody = document.getElementById("comparativa-tbody");
        if (!tbody) return;
        tbody.innerHTML = "";

        if (data.success && data.comparativa) {
            // Ordenar: Agotados primero, luego por cantidad consumida
            data.comparativa.sort((a, b) => {
                const stockA = a.stock || 0;
                const stockB = b.stock || 0;
                if (stockA <= 0 && stockB > 0) return -1;
                if (stockB <= 0 && stockA > 0) return 1;
                return b.consumido - a.consumido;
            });

            data.comparativa.forEach(item => {
                const tr = document.createElement("tr");

                let stockClass = "stock-ok";
                if (item.stock <= 0) stockClass = "stock-critico";
                else if (item.stock < 5) stockClass = "stock-warning";

                tr.innerHTML = `
                    <td>
                        <div style="font-weight: 600; color: #fff; font-size: 13px;">${item.nombre}</div>
                        <div style="font-size: 10px; color: #666;">${item.unidad}</div>
                    </td>
                    <td style="text-align: center;">
                        <span style="color: #ff6b6b; font-weight: bold; font-size: 14px;">${item.consumido}</span> 
                    </td>
                    <td style="text-align: right;">
                        <span class="stock-badge ${stockClass}">${item.stock}</span>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        console.error("Error cargando comparativa:", e);
    }
}

// 2. BUSQUEDA DE PLATOS (RECETAS)
async function buscarProductos() {
    const term = document.getElementById("searchTerm").value.trim();
    const container = document.getElementById("productos-container");
    if (!container) return;

    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Cargando menú...</p></div>';

    try {
        const response = await fetch("/get_recetas_empleado", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ termino: term })
        });
        const data = await response.json();

        container.innerHTML = "";
        if (data.success && data.recetas && data.recetas.length > 0) {
            data.recetas.forEach(receta => {
                const card = document.createElement("div");
                card.className = "producto-card";
                card.onclick = () => agregarAlConsumo(receta);

                card.innerHTML = `
                    <div class="producto-card-img">
                        <img src="${receta.foto || '/static/image/ramen.png'}" alt="Plato"
                             onerror="this.onerror=null; this.src='/static/image/ramen.png';">
                    </div>
                    <div class="producto-card-info">
                        <h4>${receta.nombre}</h4>
                        <span class="producto-categoria">${receta.categoria || 'Especialidad'}</span>
                    </div>
                    <button class="add-btn" title="Agregar">+</button>
                `;
                container.appendChild(card);
            });
        } else {
            container.innerHTML = '<div class="empty-state"><p>No se encontraron platos.</p></div>';
        }
    } catch (err) {
        container.innerHTML = '<div class="empty-state"><p>Error al conectar con la cocina.</p></div>';
    }
}

// 3. GESTION DE CARRITO
function agregarAlConsumo(receta) {
    const itemExistente = carritoConsumo.find(item => item.id_receta === receta.id_receta);
    if (itemExistente) {
        itemExistente.cantidad += 1;
    } else {
        carritoConsumo.push({
            id_receta: receta.id_receta,
            nombre: receta.nombre,
            cantidad: 1,
            breakdown: null,
            showBreakdown: false
        });
    }
    renderizarConsumo();
}

function renderizarConsumo() {
    const lista = document.getElementById("consumo-lista");
    const countBadge = document.getElementById("consumo-count");
    if (!lista) return;

    lista.innerHTML = "";

    if (carritoConsumo.length === 0) {
        lista.innerHTML = '<li class="empty-cart"><p>No hay platos seleccionados</p></li>';
        if (countBadge) countBadge.innerText = "0";
        return;
    }

    if (countBadge) countBadge.innerText = carritoConsumo.reduce((acc, item) => acc + item.cantidad, 0);

    carritoConsumo.forEach((item, idx) => {
        const li = document.createElement("li");
        li.className = "consumo-item-block";
        li.style.cssText = "display:flex; flex-direction:column; padding:12px 0; border-bottom:1px solid rgba(255,255,255,0.05);";

        li.innerHTML = `
            <div class="consumo-item" style="display:flex; justify-content:space-between; align-items:center;">
                <div class="consumo-item-info">
                    <span class="consumo-item-name" style="color:#fff; font-weight:600; font-size:13px;">${item.nombre}</span>
                    <button class="toggle-breakdown" onclick="toggleBreakdown(${idx})" style="display:block;">
                        ${item.showBreakdown ? 'Ocultar ingredientes' : 'Ver ingredientes'}
                    </button>
                </div>
                <div class="consumo-item-controls" style="display:flex; align-items:center; gap:8px;">
                    <button class="qty-btn" onclick="actualizarCantidad(${idx}, -1)">-</button>
                    <input type="number" 
                           class="qty-input" 
                           value="${item.cantidad}" 
                           min="1" 
                           max="500"
                           onchange="cambioManualCantidad(${idx}, this.value)"
                           style="width:50px; text-align:center; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); color:#fff; border-radius:5px; font-weight:bold; height:30px;">
                    <button class="qty-btn" onclick="actualizarCantidad(${idx}, 1)">+</button>
                    <button class="remove-btn" onclick="eliminarDelCarrito(${idx})" style="padding:5px;">×</button>
                </div>
            </div>
            <div id="breakdown-${idx}" class="breakdown-container" style="display: ${item.showBreakdown ? 'block' : 'none'}; margin-top:10px;">
                ${renderBreakdownContent(item.breakdown)}
            </div>
        `;
        lista.appendChild(li);
    });
}

function renderBreakdownContent(breakdown) {
    if (!breakdown) return '<p style="font-size:10px; color:#666;">Cargando receta...</p>';
    if (breakdown.length === 0) return '<p style="font-size:10px; color:#666;">Sin ingredientes registrados.</p>';

    return breakdown.map(ing => `
        <div class="breakdown-item" style="display:flex; justify-content:space-between; font-size:11px; color:#aaa; padding:2px 0;">
            <span>${ing.nombre}</span>
            <span style="color:#ff6b6b;">${ing.cantidad} ${ing.unidad}</span>
        </div>
    `).join('');
}

async function toggleBreakdown(idx) {
    const item = carritoConsumo[idx];
    item.showBreakdown = !item.showBreakdown;

    if (item.showBreakdown && !item.breakdown) {
        try {
            const res = await fetch('/get_receta_breakdown', {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id_receta: item.id_receta })
            });
            const data = await res.json();
            if (data.success) {
                item.breakdown = data.breakdown;
            }
        } catch (e) {
            console.error("Error breakdown:", e);
        }
    }
    renderizarConsumo();
}

function actualizarCantidad(idx, delta) {
    let nueva = carritoConsumo[idx].cantidad + delta;
    if (nueva < 1) {
        eliminarDelCarrito(idx);
    } else {
        if (nueva > 500) nueva = 500;
        carritoConsumo[idx].cantidad = nueva;
        renderizarConsumo();
    }
}

function cambioManualCantidad(idx, valor) {
    let num = parseInt(valor);
    if (isNaN(num) || num < 1) num = 1;
    if (num > 500) {
        alertaNinja("warning", "CANTIDAD MÁXIMA", "El límite por registro es de 500 unidades.");
        num = 500;
    }
    carritoConsumo[idx].cantidad = num;
    renderizarConsumo();
}

function eliminarDelCarrito(idx) {
    carritoConsumo.splice(idx, 1);
    renderizarConsumo();
}

// 4. REGISTRO FINAL
async function confirmarConsumo() {
    if (carritoConsumo.length === 0) {
        return alertaNinja("info", "CARRITO VACÍO", "Selecciona platos para registrar la venta.");
    }

    const { isConfirmed } = await confirmarNinja(
        '¿CONFIRMAR VENTA?',
        `Se procesará el descuento de inventario para ${carritoConsumo.length} tipos de platos.`
    );

    if (isConfirmed) {
        Swal.fire({
            title: 'Procesando...',
            allowOutsideClick: false,
            background: 'rgba(10, 10, 10, 0.95)',
            color: '#fff',
            didOpen: () => { Swal.showLoading(); }
        });

        try {
            for (const item of carritoConsumo) {
                const res = await fetch('/registrar_consumo_receta', {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        id_receta: item.id_receta,
                        cantidad: item.cantidad
                    })
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.msg); // El backend ya trae el mensaje detallado
            }

            Swal.fire({
                title: '¡Venta Registrada!',
                text: 'El inventario ha sido actualizado.',
                icon: 'success',
                background: 'rgba(10, 10, 10, 0.95)',
                color: '#fff',
                timer: 2000,
                showConfirmButton: false
            });

            carritoConsumo = [];
            renderizarConsumo();
            cargarHistorialHoy();
            initComparativa();
        } catch (err) {
            alertaNinja("error", "ERROR DE INVENTARIO", err.message);
        }
    }
}

// 5. HISTORIAL
async function cargarHistorialHoy() {
    const tbody = document.getElementById("historial-tbody");
    const emptyMsg = document.getElementById("historial-empty");
    if (!tbody) return;

    try {
        const res = await fetch("/historial_consumo_hoy");
        const data = await res.json();

        if (data.success && data.consumos && data.consumos.length > 0) {
            if (emptyMsg) emptyMsg.style.display = "none";
            tbody.innerHTML = data.consumos.map(c => {
                const hora = new Date(c.fecha).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `
                    <tr>
                        <td>${hora}</td>
                        <td>${c.nombre_producto}</td>
                        <td class="text-center">${c.cantidad}</td>
                        <td>${c.unidad}</td>
                        <td>General</td>
                    </tr>
                `;
            }).join("");
        } else {
            if (emptyMsg) emptyMsg.style.display = "flex";
            tbody.innerHTML = "";
        }
    } catch (e) {
        console.error("Error historial:", e);
    }
}
