document.getElementById('registerForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData();
    formData.append("nombre", document.getElementById('nombre').value);
    formData.append("cedula", document.getElementById('cedula').value);
    formData.append("contrasena", document.getElementById('contrasena').value);
    formData.append("contacto", document.getElementById('contacto').value);

    const fotoFile = document.getElementById('foto').files[0];
    if (fotoFile) {
        formData.append("foto", fotoFile);
    }

    const response = await fetch('/registrar_empleado', {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    document.getElementById('registerMsg').innerText = data.msg;

    if (data.success) {
        document.getElementById('registerForm').reset();
        setTimeout(() => window.location.reload(), 1000);
    }
});



window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
        window.location.reload();
    }
});

// Vista previa de la foto antes de registrar
document.getElementById('foto').addEventListener('change', function() {
    const file = this.files[0];
    const preview = document.getElementById('previewFoto');

    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = "block";
        };
        reader.readAsDataURL(file);
    } else {
        preview.src = "";
        preview.style.display = "none";
    }
});


document.getElementById("buscarEmpleado").addEventListener("input", async function() {
  let termino = this.value.trim();
  let resultBox = document.getElementById("resultEmpleado");

  if (termino.length === 0) {
    resultBox.innerHTML = "<p>No se ha realizado ninguna búsqueda</p>";
    return;
  }

  try {
    const response = await fetch("/buscar_empleado", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ termino })
    });

    const data = await response.json();

    if (data.success) {
      resultBox.innerHTML = data.empleados.map(emp => `
        <div class="empleado-card">
          <div style="display: flex; align-items: center; gap: 15px;">
            <img src="${emp.Foto ? emp.Foto : '/static/image/default.png'}" 
              alt="Foto de ${emp.Nombre}" 
              style="width:60px; height:60px; border-radius:50%; object-fit:cover;">
            <div class="empleado-info">
              <p><strong>${emp.Nombre}</strong></p>
              <p>ID: ${emp.Cedula}</p>
              <p>Contacto: ${emp.Numero_contacto}</p>
            </div>
          </div>
          <div class="empleado-actions">
            <button onclick="eliminarEmpleado('${emp.Cedula}')">Eliminar</button>
          </div>
        </div>
      `).join("");
    } else {
      resultBox.innerHTML = "<p>" + data.msg + "</p>";
    }

  } catch (err) {
    console.error("Error en la búsqueda:", err);
    resultBox.innerHTML = "<p>Error en el servidor</p>";
  }
});


function mostrarResultados(data) {
  const contenedor = document.getElementById("resultEmpleado");
  contenedor.innerHTML = ""; // limpio resultados

  if (data.length === 0) {
    contenedor.innerHTML = "<p>No se encontraron empleados</p>";
    return;
  }

  data.forEach(emp => {
    const card = document.createElement("div");
    card.classList.add("empleado-card");

    card.innerHTML = `
      <div style="display: flex; align-items: center; gap: 15px;">
        <img src="${emp.foto || '/static/image/default.png'}" alt="Foto de ${emp.nombre}">
        <div class="empleado-info">
          <strong>${emp.nombre}</strong>
          <span>ID: ${emp.id}</span>
          <span>Contacto: ${emp.contacto}</span>
        </div>
      </div>
      <div class="empleado-actions">
        <button onclick="eliminarEmpleado('${emp.id}')">Eliminar</button>
      </div>
    `;

    contenedor.appendChild(card);
  });
}

function eliminarEmpleado(id) {
    Swal.fire({
        title: '¿Estás seguro?',
        text: "Esta acción eliminará al empleado",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#aaa',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
        background: '#000',
        color: '#fff',
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/eliminar_empleado/${id}`, {
                method: 'DELETE'
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Empleado eliminado',
                        text: 'El registro fue eliminado correctamente',
                        confirmButtonColor: '#e60000',
                        background: '#000',
                        color: '#fff'
                    });
                    document.getElementById("buscarEmpleado").dispatchEvent(new Event("input")); // refresca lista
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: data.msg,
                        confirmButtonColor: '#e60000',
                        background: '#000',
                        color: '#fff'
                    });
                }
            });
        }
    });
}


