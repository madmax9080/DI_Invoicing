import { apiFetch } from "../api.js";
import { showToast } from "../toast.js";

let allClients = [];
document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "/index.html";
        return;
    }
    setupEvents();
    setupSearch();
    // setupLogout();
    loadClients();
});

function setupEvents() {
    document.addEventListener("click", (e) => {
        if (e.target.closest("#newClientBtn, .add-card, #emptyAddBtn")) {
            clearForm();
            const modal = new bootstrap.Modal(document.getElementById("addClientModal"));
            modal.show();
        }
        if (e.target.id === "saveClientBtn") {
            handleCreateClient();
        }
    });
    document.getElementById("addClientModal")
        .addEventListener("shown.bs.modal", loadProvinces);
}

const PROVINCES = [
    { id: 2, text: "BALOCHISTAN" },
    { id: 4, text: "AZAD JAMMU AND KASHMIR" },
    { id: 5, text: "CAPITAL TERRITORY" },
    { id: 6, text: "KHYBER PAKHTUNKHWA" },
    { id: 7, text: "PUNJAB" },
    { id: 8, text: "SINDH" },
    { id: 9, text: "GILGIT BALTISTAN" }
];

function loadProvinces() {
    const select = document.getElementById("clientProvinceInput");
    select.innerHTML = `<option value="">Select province...</option>`;
    PROVINCES.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.text;
        select.appendChild(opt);
    });
}

async function handleCreateClient() {
    const btn = document.getElementById("saveClientBtn");
    btn.disabled = true;
    btn.innerText = "Saving...";
    const payload = {
        name: document.getElementById("clientNameInput").value.trim(),
        sellerNTNCNIC: document.getElementById("clientNTNInput").value.trim(),
        sellerBusinessName: document.getElementById("clientBusinessInput").value.trim(),
        sellerProvince: document.getElementById("clientProvinceInput").value,
        sellerAddress: document.getElementById("clientAddressInput").value.trim(),
        token: document.getElementById("clientTokenInput").value.trim()
    };
    for (const [key, val] of Object.entries(payload)) {
        if (!val) {
            showToast(`${key} is required`, "warning");
            resetBtn();
            return;
        }
    }
    const ntn = payload.sellerNTNCNIC;
    if (!/^\d+$/.test(ntn)) {
        showToast("Registration number must contain digits only", "warning");
        resetBtn();
        return;
    }
    if (ntn.length !== 7 && ntn.length !== 13) {
        showToast("Enter valid NTN (7 digits) or CNIC (13 digits)", "warning");
        resetBtn();
        return;
    }
    try {
        const data = await apiFetch("/clients/", {
            method: "POST",
            body: payload
        });
        showToast("Client created successfully", "success");
        bootstrap.Modal.getInstance(
            document.getElementById("addClientModal")
        ).hide();
        clearForm();
        await loadClients();
    } catch (err) {
        showToast(err.message || "Error creating client", "danger");
    } finally {
        resetBtn();
    }
    function resetBtn() {
        btn.disabled = false;
        btn.innerText = "Save Client →";
    }
}

async function loadClients() {
    try {
        const clients = await apiFetch("/clients/");
        allClients = clients || [];
        renderClients(allClients);
    } catch (err) {
        console.error(err);
        showToast("Failed to load clients", "danger");
    }
}

function renderClients(clients) {
    const grid = document.getElementById("clientGrid");
    const countBadge = document.getElementById("clientCount");
    grid.innerHTML = "";
    if (countBadge) {
        countBadge.textContent = clients.length;
    }
    const savedClient = localStorage.getItem("client_id");
    if (!clients.length) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-card">
                    <div class="empty-icon">🏢</div>
                    <h2>No Clients Yet</h2>
                    <p>Create your first workspace to continue with a polished invoicing flow.</p>
                    <button class="btn empty-btn" id="emptyAddBtn">
                        + Add Your First Client
                    </button>
                </div>
            </div>
        `;
        return;
    }
    clients.forEach(client => {
        const initials = client.name
            .split(" ")
            .map(w => w[0])
            .join("")
            .toUpperCase();
        const div = document.createElement("div");
        div.className = "client-card";
        if (client.id == savedClient) {
            div.classList.add("active");
        }
        div.innerHTML = `
            <div class="card-top">
                <div class="avatar">${initials}</div>
                <div class="status-dot"></div>
            </div>
            <div class="card-body">
                <h3>${client.sellerBusinessName}</h3>
                <p class="client-name">${client.name}</p>
            </div>
        `;
        div.onclick = () => {
            localStorage.setItem(
                "client_id",
                client.id
            );
            localStorage.setItem(
                "client_name",
                client.name
            );
            localStorage.setItem(
                "client_business",
                client.sellerBusinessName
            );
            const initials =
                client.name
                    .split(" ")
                    .map(w => w[0])
                    .join("")
                    .substring(0, 2)
                    .toUpperCase();
            localStorage.setItem(
                "client_avatar",
                initials
            );
            window.location.href = "/layout.html";
        };
        grid.appendChild(div);
    });
    const add = document.createElement("div");
    add.className = "client-card add-card";
    add.innerHTML = "+";
    grid.appendChild(add);
}

function setupSearch() {
    const input = document.getElementById("searchInput");
    input.addEventListener("input", (e) => {
        const value = e.target.value.toLowerCase();
        const filtered = allClients.filter(c =>
            c.sellerBusinessName.toLowerCase().includes(value)
        );
        renderClients(filtered);
    });
}

// function setupLogout() {
//     document.getElementById("logoutBtn").addEventListener("click", () => {
//         localStorage.clear();
//         sessionStorage.clear();
//         window.location.href = "/index.html";
//     });
// }

function clearForm() {
    document.querySelectorAll("input, textarea").forEach(el => el.value = "");
    document.getElementById("clientProvinceInput").value = "";
}