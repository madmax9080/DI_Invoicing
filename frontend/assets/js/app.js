import { apiFetch } from "./api.js";
let allClients = [];
const routes = {
    dashboard: {
        page: "/pages/dashboard.html",
        url: "#dashboard",
        script: "/assets/js/pages/dashboard.js",
        init: "initDashboard",
        destroy: "destroyDashboard"
    },
    create_invoice: {
        page: "/pages/create_invoice.html",
        url: "#create-invoice",
        script: "/assets/js/pages/create_invoice.js",
        init: "initCreateInvoice",
        destroy: "destroyCreateInvoice"
    },
    reports: {
        page: "/pages/reports.html",
        url: "#reports",
        script: "/assets/js/pages/reports.js",
        init: "initReports",
        destroy: "destroyReports"
    },
    seller_profile: {
        page: "/pages/clients.html",
        url: "#profile",
        script: "/assets/js/pages/clients.js",
        init: "initClients",
        destroy: "destroyClients"
    },
    import_excel: {
        page: "/pages/excel_import.html",
        url: "#import",
        script: "/assets/js/pages/excel.js",
        init: "initExcelImport",
        destroy: "destroyExcelImport"
    },
    buyers: {
        page: "/pages/buyer.html",
        url: "#buyers",
        script: "/assets/js/pages/buyers.js",
        init: "initBuyers",
        destroy: "destroyBuyers"
    },
};

let currentRoute = "dashboard";
let currentModule = null;
let isRouting = false;
async function loadClients() {
    try {
        const clients =
            await apiFetch("/clients/");
        allClients = clients;
        let savedClient =
            localStorage.getItem(
                "client_id"
            );
        if (
            (
                !savedClient ||
                savedClient === "null" ||
                savedClient === "undefined"
            ) &&
            clients.length
        ) {
            savedClient = clients[0].id;
            localStorage.setItem(
                "client_id",
                savedClient
            );
        }
        const selectedClient =
            clients.find(
                c => c.id == savedClient
            );
        if (selectedClient) {
            localStorage.setItem(
                "client_name",
                selectedClient.name
            );
            localStorage.setItem(
                "client_business",
                selectedClient
                    .sellerBusinessName || ""
            );
            const initials =
                selectedClient.name
                    .split(" ")
                    .map(w => w[0])
                    .join("")
                    .substring(0, 2)
                    .toUpperCase();
            localStorage.setItem(
                "client_avatar",
                initials
            );
            updateClientUI();
        }
    } catch (err) {
        console.error(
            "Client load failed:",
            err
        );
        alert(
            "Unable to load clients"
        );
    }
}

function updateClientUI() {
    const clientName =
        localStorage.getItem("client_name");
    const clientBusiness =
        localStorage.getItem("client_business");
    if (!clientName) return;
    $("#clientNameDisplay").text(clientName);
    $("#clientBusiness").text(
        clientBusiness || ""
    );
    const initials = clientName
        .split(" ")
        .map(w => w[0])
        .join("")
        .substring(0, 2)
        .toUpperCase();
    $("#clientAvatar").text(initials);
}

function getHeaderClientName() {
    const clientName = localStorage.getItem("client_name") || "";
    return clientName || "there";
}

function getHeaderSubtitle() {
    const selectedFY = localStorage.getItem("selectedFY");
    if (!selectedFY) {
        return "Here's your business overview.";
    }
    return `Here's your business overview for FY ${selectedFY}`;
}

function updateHeaderUI() {
    const clientName = getHeaderClientName();
    const greeting = getGreeting();
    $(".welcome-title").html(`${greeting}, <span id="headerUserName">${clientName}</span> <span class="wave">👋</span>`);
    $("#welcomeSubtitle").text(getHeaderSubtitle());
}

async function loadRoute(routeName, updateHash = true) {
    if (isRouting) {
        return;
    }
    const route = routes[routeName];
    if (!route) {
        return;
    }
    isRouting = true;
    try {
        if (currentModule && currentRoute) {
            const currentRouteConfig =
                routes[currentRoute];
            const destroyFnName =
                currentRouteConfig?.destroy;
            const destroyFn =
                currentModule?.[destroyFnName];
            if (typeof destroyFn === "function") {
                try {
                    destroyFn();
                } catch (destroyErr) {
                    console.error(
                        "Page destroy failed:",
                        destroyErr
                    );
                }
            }
        }
        currentRoute = routeName;
        if (updateHash) {
            if (window.location.hash !== route.url) {
                history.pushState(
                    { route: routeName },
                    "",
                    route.url
                );
            }
        }
        $("#pageTitle").text(route.title);
        $("#pageSubtitle").text(route.subtitle);
        $(".menu-item")
            .removeClass("active");
        $(`.menu-item[data-route="${routeName}"]`)
            .addClass("active");
        const html = await fetch(
            route.page,
            {
                cache: "no-store"
            }
        ).then(r => r.text());
        $("#appContent").html(html);
        const module = await import(route.script);
        currentModule = module;
        const initFn = module[route.init];
        if (typeof initFn === "function") {
            await initFn();
        }
    } catch (err) {
        console.error(
            "Route load failed:",
            err
        );
        $("#appContent").html(`
            <div class="p-4 text-danger">
                Failed to load page
            </div>
        `);
    } finally {
        isRouting = false;
    }
}

window.addEventListener("hashchange", async () => {
    if (isRouting) {
        return;
    }
    const currentHash =
        window.location.hash;
    const matchedRoute =
        Object.keys(routes).find(
            key => routes[key].url === currentHash
        );
    if (
        matchedRoute &&
        matchedRoute !== currentRoute
    ) {
        await loadRoute(
            matchedRoute,
            false
        );
    }
});

function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    return "Good Evening";
}

$(document).ready(async function () {
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "/index.html";
        return;
    }
    await loadClients();
    updateClientUI();
    updateHeaderUI();
    $(document).on("selectedFYChanged", updateHeaderUI);
    const currentHash = window.location.hash || "#dashboard";
    const matchedRoute =
        Object.keys(routes).find(
            key => routes[key].url === currentHash
        );
    await loadRoute(
        matchedRoute || currentRoute,
        false
    );
    history.replaceState(
        { route: matchedRoute || currentRoute },
        "",
        routes[matchedRoute || currentRoute].url
    );
    $(".menu-item").click(function () {
        const route = $(this).data("route");
        if (route) {
            loadRoute(route);
        }
    });
    document
        .getElementById("switchClientBtn")
        .addEventListener("click", () => {
            localStorage.clear();
            sessionStorage.clear();
            window.location.replace("/index.html");
        });
    $("#logoutBtn").click(function () {
        localStorage.clear();
        sessionStorage.clear();
        window.location.replace("/index.html");
    });
});