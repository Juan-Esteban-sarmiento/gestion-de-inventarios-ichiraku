// 🎴 ALERTA NINJA GLOBAL
function alertaNinja(icon, title, text) {
    const iconColors = { success:'#00ff7f', error:'#ff3333', warning:'#ffcc00', info:'#ffffff', question:'#e60000' };
    Swal.fire({
        icon: icon,
        title: `<span style="font-family:njnaruto; color:#fff;">${title}</span>`,
        text: text || '',
        background: '#000',
        color: '#fff',
        iconColor: iconColors[icon] || '#e60000',
        confirmButtonColor: '#e60000',
        confirmButtonText: '<span style="font-family:njnaruto;">Aceptar</span>',
    });
}

// 🔽 Mostrar / Ocultar detalles del pedido
function toggleDetalles(idPedido) {
    document.querySelectorAll(".productos-detalle").forEach(detalle => {
        if (detalle.id !== `detalles-${idPedido}`) detalle.style.display = "none";
    });
    const detalles = document.getElementById(`detalles-${idPedido}`);
    detalles.style.display = detalles.style.display === "block" ? "none" : "block";
}

// ✅ Autocompletar formulario
function autocompletarFormulario(idPedido, idProducto, nombre, categoria, cantidad, unidad) {
    document.getElementById("id_pedido").value = idPedido;
    document.getElementById("id_producto").value = idProducto;
    document.getElementById("nombre_producto").value = nombre;
    document.getElementById("categoria").value = categoria;
    document.getElementById("cantidad").value = cantidad;
    document.getElementById("unidad").value = unidad;

    const fechaFila = document.getElementById(`fecha_caducidad-${idPedido}-${idProducto}`);
    document.getElementById("fecha_caducidad").value = fechaFila.value || "";

    document.querySelectorAll(".tabla-productos tr").forEach(row => row.classList.remove("seleccionado"));
    document.getElementById(`prod-${idPedido}-${idProducto}`).classList.add("seleccionado");
}

// 🟢 Guardar confirmaciones
function guardarConfirmado(idPedido, idProducto) {
    const data = JSON.parse(localStorage.getItem("confirmaciones")) || {};
    data[`${idPedido}-${idProducto}`] = true;
    localStorage.setItem("confirmaciones", JSON.stringify(data));
}

// 🔄 Cargar confirmaciones al iniciar
function cargarConfirmaciones() {
    const data = JSON.parse(localStorage.getItem("confirmaciones")) || {};
    Object.keys(data).forEach(key => {
        const [idPedido, idProducto] = key.split("-");
        const fila = document.querySelector(`#detalles-${idPedido} #prod-${idPedido}-${idProducto}`);
        if(fila) {
            fila.classList.add("confirmado");
            const btn = fila.querySelector(".btn-registro");
            if(btn){ btn.disabled=true; btn.innerText="✅ Confirmado"; }
        }
    });
}

// 🟡 Marcar pedidos recibidos
function marcarPedidosRecibidos() {
    document.querySelectorAll(".pedido-item").forEach(pedido => {
        const estadoTexto = pedido.querySelector("p strong")?.parentElement?.textContent || "";
        if (estadoTexto.includes("Recibido")) {
            pedido.classList.add("recibido");
            pedido.querySelectorAll(".btn-registro").forEach(btn => { btn.disabled=true; btn.innerText="✅ Confirmado"; });
            const detalles = pedido.querySelector(".productos-detalle");
            if(detalles) detalles.style.display="none";
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    cargarConfirmaciones();
    marcarPedidosRecibidos();

    const form = document.getElementById("recepcionForm");
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const idPedido = document.getElementById("id_pedido").value;
        const idProducto = document.getElementById("id_producto").value;
        const fechaCad = document.getElementById("fecha_caducidad").value;
        const cantidad = document.getElementById("cantidad").value;

        if(!idPedido || !idProducto || !fechaCad || !cantidad){
            alertaNinja('warning','Campos incompletos','Selecciona un producto y completa los campos.');
            return;
        }

        try{
            const response = await fetch("/Em_Rordenes", {
                method:"POST",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({id_pedido:idPedido,id_producto:idProducto,cantidad:cantidad,fecha_caducidad:fechaCad})
            });

            const result = await response.json();
            if(result.success){
                const row = document.querySelector(`#detalles-${idPedido} #prod-${idPedido}-${idProducto}`);
                row.classList.add("confirmado");
                const btn = row.querySelector(".btn-registro");
                if(btn){ btn.disabled=true; btn.innerText="✅ Confirmado"; }

                guardarConfirmado(idPedido,idProducto);

                // Mostrar botón solo si todos los productos están confirmados
                const allRows = document.querySelectorAll(`#detalles-${idPedido} tbody tr`);
                const allConfirmed = Array.from(allRows).every(r=>r.classList.contains("confirmado"));
                if(allConfirmed) mostrarBotonConfirmarPedido(idPedido);

                alertaNinja('success','Producto confirmado','Producto registrado correctamente.');
            } else {
                alertaNinja('error','Error',result.msg || 'No se pudo confirmar el producto.');
            }
        } catch(err){
            console.error("Error al confirmar producto:",err);
            alertaNinja('error','Error','No se pudo conectar con el servidor.');
        }
    });
});


function mostrarBotonConfirmarPedido(idPedido){
    const pedidoDiv = document.getElementById(`pedido-${idPedido}`);
    const allRows = pedidoDiv.querySelectorAll("tbody tr");
    const allConfirmed = Array.from(allRows).every(r => r.classList.contains("confirmado"));

    if(allConfirmed && !pedidoDiv.querySelector(".btn-confirmar-pedido")){
        const btn = document.createElement("button");
        btn.classList.add("btn","btn-confirmar-pedido");
        btn.innerText = "Confirmar pedido completo";
        btn.onclick = () => confirmarPedidoCompleto(idPedido);
        pedidoDiv.appendChild(btn);
    }
}


function confirmarPedidoCompleto(idPedido) {
    if (!idPedido || isNaN(idPedido)) {
        alertaNinja('error','Error','id_pedido inválido.');
        return;
    }

    Swal.fire({
        title: '<span style="font-family:njnaruto; color:#fff;">¿Confirmar pedido completo?</span>',
        text: 'El pedido será marcado como recibido.',
        icon: 'question',
        background: '#000',
        color: '#fff',
        showCancelButton: true,
        confirmButtonText: '<span style="font-family:njnaruto;">Sí, confirmar</span>',
        cancelButtonText: '<span style="font-family:njnaruto;">Cancelar</span>',
        confirmButtonColor: '#00ff7f',
        cancelButtonColor: '#6c757d',
        iconColor: '#00ff7f'
    }).then(async (result) => {
        if (!result.isConfirmed) return;

        try {
            const response = await fetch("/actualizar_estado", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({id_pedido: Number(idPedido)})
            });

            const data = await response.json();

            if (data.success) {
                const pedidoDiv = document.getElementById(`pedido-${idPedido}`);
                pedidoDiv.classList.add("recibido");

                const estado = pedidoDiv.querySelector("p strong");
                if (estado) estado.innerHTML = "📦 Pedido recibido";

                eliminarConfirmacionesDePedido(idPedido);

                alertaNinja('success','Pedido confirmado','Todos los productos fueron recibidos.');
            } else {
                alertaNinja('error','Error', data.msg || 'No se pudo actualizar el estado.');
            }
        } catch (err) {
            console.error("Error al actualizar pedido:", err);
            alertaNinja('error','Error','No se pudo conectar con el servidor.');
        }
    });
}

// 🧹 Eliminar confirmaciones de un pedido
function eliminarConfirmacionesDePedido(idPedido){
    const data=JSON.parse(localStorage.getItem("confirmaciones"))||{};
    for(const key in data) if(key.startsWith(`${idPedido}-`)) delete data[key];
    localStorage.setItem("confirmaciones",JSON.stringify(data));
}
