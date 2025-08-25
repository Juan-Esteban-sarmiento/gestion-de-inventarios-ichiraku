function login() {
    const id = document.getElementById("id").value;
    const password = document.getElementById("password").value;
    const role = document.getElementById("role").value;

    if (!id || !password || role === "-- Select --") {
    alert("Por favor completa todos los campos.");
    } else {
    alert("Bienvenido " + role + " con ID: " + id);
    }
}
