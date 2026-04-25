/**
 * Merma.js - Logica para el registro de errores humanos y mermas
 */

function abrirModalMerma() {
    document.getElementById('mermaModal').style.display = 'flex';
    document.getElementById('mermaSearch').focus();
}

function cerrarModalMerma() {
    document.getElementById('mermaModal').style.display = 'none';
    limpiarFormularioMerma();
}

function limpiarFormularioMerma() {
    document.getElementById('mermaSearch').value = '';
    document.getElementById('mermaResults').style.display = 'none';
    document.getElementById('productoSeleccionadoMerma').style.display = 'none';
    document.getElementById('mermaProdId').value = '';
    document.getElementById('mermaProdName').innerText = '';
    document.getElementById('mermaCantidad').value = '';
    document.getElementById('mermaUnidad').value = '';
    document.getElementById('mermaMotivo').value = '';
}

async function buscarProductosMerma() {
    const termino = document.getElementById('mermaSearch').value.trim();
    if (!termino) return;

    const resultsDiv = document.getElementById('mermaResults');
    resultsDiv.innerHTML = '<p style="padding: 10px; color: #666;">Buscando...</p>';
    resultsDiv.style.display = 'block';

    try {
        const response = await fetch('/buscar_producto_empleado', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ termino })
        });
        const data = await response.json();

        if (data.success && data.productos.length > 0) {
            resultsDiv.innerHTML = '';
            data.productos.forEach(p => {
                const div = document.createElement('div');
                div.className = 'merma-search-item';
                div.style.cssText = 'padding: 12px 20px; border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer; transition: 0.2s;';
                div.onmouseover = () => {
                    div.style.background = 'rgba(179,0,0,0.1)';
                    div.style.color = '#fff';
                };
                div.onmouseout = () => {
                    div.style.background = 'transparent';
                    div.style.color = 'inherit';
                };
                div.innerHTML = `<strong>${p.nombre}</strong> <small style="color: #ff6b6b; margin-left:8px;">${p.unidad}</small>`;
                div.onclick = () => seleccionarProductoMerma(p);
                resultsDiv.appendChild(div);
            });
        } else {
            resultsDiv.innerHTML = '<p style="padding: 10px; color: #e74c3c;">No se encontraron productos.</p>';
        }
    } catch (error) {
        console.error('Error buscando productos merma:', error);
        resultsDiv.innerHTML = '<p style="padding: 10px; color: #e74c3c;">Error en la busqueda.</p>';
    }
}

function seleccionarProductoMerma(producto) {
    document.getElementById('mermaResults').style.display = 'none';
    document.getElementById('productoSeleccionadoMerma').style.display = 'block';
    
    document.getElementById('mermaProdName').innerText = producto.nombre;
    document.getElementById('mermaProdId').value = producto.id_producto;
    document.getElementById('mermaUnidad').value = producto.unidad;
    
    document.getElementById('mermaCantidad').focus();
}

async function guardarMerma() {
    const id_producto = document.getElementById('mermaProdId').value;
    const cantidad = document.getElementById('mermaCantidad').value;
    const motivo = document.getElementById('mermaMotivo').value.trim();
    const btn = document.getElementById('btnGuardarMerma');

    if (!id_producto) {
        alertaNinja("Por favor seleccione un producto", "warning");
        return;
    }
    if (!cantidad || cantidad <= 0) {
        alertaNinja("Ingrese una cantidad valida", "warning");
        return;
    }
    if (!motivo) {
        alertaNinja("Por favor indique el motivo del error/merma", "warning");
        return;
    }

    btn.disabled = true;
    btn.innerText = "Registrando...";

    try {
        const response = await fetch('/registrar_merma', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_producto, cantidad, motivo })
        });
        const data = await response.json();

        if (data.success) {
            alertaNinja("Registro de merma exitoso", "success");
            cerrarModalMerma();
            // Refrescar comparativa si existe la funcion en Consumo.js
            if (typeof initComparativa === 'function') initComparativa();
            if (typeof cargarHistorialHoy === 'function') cargarHistorialHoy();
        } else {
            alertaNinja(data.msg || "Error al registrar merma", "error");
        }
    } catch (error) {
        console.error('Error al guardar merma:', error);
        alertaNinja("Error de conexion al servidor", "error");
    } finally {
        btn.disabled = false;
        btn.innerText = "Confirmar Registro";
    }
}

// Permitir buscar con Enter
document.getElementById('mermaSearch')?.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        buscarProductosMerma();
    }
});
