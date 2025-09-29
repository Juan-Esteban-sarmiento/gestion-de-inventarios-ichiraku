function descargar(idInforme) {
    window.location.href = `/descargar_informe/${idInforme}`;
}

document.addEventListener('DOMContentLoaded', function() {
    // Búsqueda
    document.getElementById('searchForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const id_informe = document.getElementById('id_informe').value.trim();
        const date = document.getElementById('date').value;
        let body = {};
        if (id_informe) {
            body.id_informe = id_informe;
        } else if (date) {
            body.fecha = date;
        } else {
            alert('Ingresa un ID de informe o una fecha para buscar.');
            return;
        }
        fetch('/buscar_informe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
        .then(res => res.json())
        .then(data => {
            const resultBox = document.getElementById('resultEmpleado');
            if(data.success && data.informes.length > 0) {
                let html = '<ul>';
                data.informes.forEach(inf => {
                    html += `
                        <li>
                            <strong>ID Informe:</strong> ${inf.Id_Informe} |
                            <strong>ID Pedido(s):</strong> ${inf.Id_Inf_Pedido} |
                            <strong>Periodo:</strong> ${inf.Periodo} |
                            <strong>Tipo:</strong> ${inf.Tipo}
                            <button onclick="descargar(${inf.Id_Informe})">Descargar</button>
                        </li>`;
                });
                html += '</ul>';
                resultBox.innerHTML = html;
            } else {
                resultBox.innerHTML = '<p>No se encontraron informes</p>';
            }
        });
    });

    // Botón generar semanal
    document.getElementById('genSemBtn').addEventListener('click', () => {
        fetch('/generar_informe_semanal', { method: 'POST' })
        .then(res => res.json())
        .then(data => alert(data.msg));
    });

    // Botón generar mensual
    document.getElementById('genMesBtn').addEventListener('click', () => {
        fetch('/generar_informe_mensual', { method: 'POST' })
        .then(res => res.json())
        .then(data => alert(data.msg));
    });

    // Botón descargar primero
    document.getElementById('downloadBtn').addEventListener('click', () => {
        const resultBox = document.getElementById('resultEmpleado');
        const match = resultBox.innerHTML.match(/descargar\((\d+)\)/);
        if(match) {
            window.open(`/descargar_informe/${match[1]}`, '_blank');
        } else {
            alert('Primero realiza una búsqueda y selecciona un informe.');
        }
    });
});

const lista = document.getElementById("listaSeleccion");

function agregarProducto(id, nombre) {
    let cantidad = prompt("Ingrese cantidad para " + nombre + ":");
    if (cantidad && cantidad > 0) {
    let li = document.createElement("li");
    li.textContent = nombre + " - Cantidad: " + cantidad;
    lista.appendChild(li);
    }
}
