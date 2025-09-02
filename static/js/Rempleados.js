document.getElementById('registerForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const nombre = document.getElementById('nombre').value;
    const cedula = document.getElementById('cedula').value;
    const contrasena = document.getElementById('contrasena').value;
    const contacto = document.getElementById('contacto').value;

    const response = await fetch('/registrar_empleado', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, cedula, contrasena, contacto })
    });

    const data = await response.json();
    document.getElementById('registerMsg').innerText = data.msg;

    if (data.success) {

        document.getElementById('registerForm').reset();

        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
});


window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
        window.location.reload();
    }
});

document.getElementById("buscarEmpleado").addEventListener("input", function() {
  let termino = this.value.trim();
  if (termino.length < 2) {
    document.getElementById("resultEmpleado").innerHTML = "<p>Busca un empleado</p>";
    return;
  }

  fetch("/buscar_empleado", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ termino: termino })
  })
  .then(res => res.json())
  .then(data => {
    let resultBox = document.getElementById("resultEmpleado");
    if (data.success) {
      let emp = data.empleado;
      resultBox.innerHTML = `
        <img src="${emp.Foto || '/static/image/default-user.png'}" alt="Foto empleado">
        <p><strong>${emp.Nombre}</strong></p>
        <p>ID: ${emp.Cedula}</p>
        <p>Contacto: ${emp.Contacto}</p>
      `;
    } else {
      resultBox.innerHTML = "<p>" + data.msg + "</p>";
    }
  });
});