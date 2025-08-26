function login(event) {
    event.preventDefault(); // evita que el form recargue la página

    const id = document.getElementById("id").value;
    const password = document.getElementById("password").value;
    const role = document.getElementById("role").value;
    const branch = document.getElementById("branch").value;

    if (!id || !password || role === "" || role === "-- Selecciona --") {
        alert("Por favor completa todos los campos.");
        return false;
    }
    if (role === "Empleado" && !branch) {
        alert("Por favor selecciona una sucursal.");
        return false;
    }

    fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, password, role, branch })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.msg);
            window.location.href = "/";
        } else {
            alert(data.msg);
        }
    })
    .catch(err => console.error(err));

    return false; // evita que el form haga submit normal
}

function toggleBranch() {
    const role = document.getElementById("role").value;
    const branchGroup = document.getElementById("branch-group");
    branchGroup.style.display = (role === "Empleado") ? "block" : "none";
}
