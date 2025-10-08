async function login(event) {
    if (event) event.preventDefault();

    const id = document.getElementById("id").value;
    const password = document.getElementById("password").value;
    const role = document.getElementById("role").value;
    let branch = "";

    if (!id || !password || !role || role === "-- Selecciona --") {
        alert("Por favor completa todos los campos.");
        return false;
    }

    if (role === "Empleado") {
        branch = document.getElementById("branch").value;
        if (!branch) {
            alert("Por favor selecciona una sucursal.");
            return false;
        }
    }

    fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, password, role, branch })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.msg || "Inicio de sesión exitoso");
            window.location.href = data.redirect || "/";
        } else {
            alert(data.msg);
        }
    })
    .catch(err => console.error(err));

    return false;
}

function logout() {
    fetch('/logout', { method: 'GET' })
        .then(() => {
            window.location.href = '/login';
        })
        .catch(err => console.error('Error al cerrar sesión:', err));
}

// Mostrar select solo si rol = Empleado
function toggleBranch() {
    const role = document.getElementById("role").value;
    const branchGroup = document.getElementById("branch-group");
    branchGroup.style.display = (role === "Empleado") ? "block" : "none";

    if (role === "Empleado") {
        cargarLocales();
    }
}


// Cargar locales desde backend
async function cargarLocales() {
    try {
        const response = await fetch("/get_locales");
        const data = await response.json();
        const select = document.getElementById("branch");

        select.innerHTML = '<option value="">-- Selecciona --</option>';

        if (data.success && data.locales.length > 0) {
            data.locales.forEach(loc => {
                const option = document.createElement("option");
                option.value = loc.id_local; // id real
                option.textContent = loc.nombre;
                select.appendChild(option);
            });
        } else {
            const option = document.createElement("option");
            option.textContent = "No hay locales disponibles";
            option.disabled = true;
            select.appendChild(option);
        }
    } catch (err) {
        console.error("Error al cargar locales:", err);
    }
}
