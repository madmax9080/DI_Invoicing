export function showToast(message, type = "info", title = "") {
    const id = `toast-${Date.now()}`;
    const typeMap = {
        success: {
            headerClass: "bg-success text-white",
            icon: "bi-check-circle"
        },
        error: {
            headerClass: "bg-danger text-white",
            icon: "bi-x-circle"
        },
        warning: {
            headerClass: "bg-warning text-dark",
            icon: "bi-exclamation-triangle"
        },
        info: {
            headerClass: "bg-primary text-white",
            icon: "bi-info-circle"
        }
    };
    const config = typeMap[type] || typeMap.info;
    const html = `
        <div id="${id}" class="toast shadow border-0 mb-3" role="alert">
            <div class="toast-header ${config.headerClass}">
                <i class="bi ${config.icon} me-2"></i>
                <strong class="me-auto">${title || type.toUpperCase()}</strong>
                <button type="button"
                        class="btn-close btn-close-white"
                        data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body bg-light text-dark fw-medium">
                ${message}
            </div>
        </div>
    `;
    const container = document.getElementById("toastContainer");
    if (!container) return;
    container.insertAdjacentHTML("beforeend", html);
    const toastEl = document.getElementById(id);
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();
    toastEl.addEventListener("hidden.bs.toast", () => toastEl.remove());
}
