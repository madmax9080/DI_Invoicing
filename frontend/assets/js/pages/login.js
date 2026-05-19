import { apiFetch } from "../api.js";
import { showToast } from "../toast.js";

const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const loginBtn = document.getElementById("loginBtn");

loginBtn.addEventListener("click", handleLogin);

document.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleLogin();
});

localStorage.clear(); 
sessionStorage.clear();
async function handleLogin() {
    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();

    if (!email || !password) {
        showToast("Please enter email and password");
        return;
    }

    loginBtn.disabled = true;
    loginBtn.innerText = "Signing in...";

    try {
        const data = await apiFetch("/auth/login", {
            method: "POST",
            body: { email, password }
        });
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user_email", email);
        const clients = await apiFetch("/clients/");
        if (!clients || clients.length === 0) {
            window.location.href = "/select_client.html";
            return;
        }

        if (clients.length === 1) {
            // ✅ Auto select single client
            localStorage.setItem("client_id", clients[0].id);
            window.location.href = "/pages/layout.html";
        } else {
            // ✅ Multiple clients → selection page
            window.location.href = "/select_client.html";
        }

    } catch (err) {
        console.error("Login failed:", err);
    } finally {
        loginBtn.disabled = false;
        loginBtn.innerText = "Sign in →";
    }
}