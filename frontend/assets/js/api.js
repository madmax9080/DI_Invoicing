import { API_BASE } from "./config.js";
import { showToast } from "./toast.js";
export async function apiFetch(endpoint, options = {}) {
    const token = localStorage.getItem("access_token");
    const clientId = localStorage.getItem("client_id");
    const fy = localStorage.getItem("selectedFY");
    const isFormData = options.body instanceof FormData;
    let url = `${API_BASE}${endpoint}`;
    // if (
    //     clientId &&
    //     // !endpoint.startsWith("/api/clients") &&
    //     !endpoint.startsWith("/clients") &&
    //     !url.includes("client_id=")
    // ) 
    // {
    //     const sep = url.includes("?") ? "&" : "?";
    //     url += `${sep}client_id=${clientId}`;
    // }
    if (
        clientId &&
        !url.includes("client_id=")
    )
    {
        const sep = url.includes("?") ? "&" : "?";

        url += `${sep}client_id=${clientId}`;
    }
    if (fy && !url.includes("fy=")) {
        const sep = url.includes("?") ? "&" : "?";
        url += `${sep}fy=${fy}`;
    }
    const headers = {
        ...(token && { Authorization: `Bearer ${token}` }),
        ...(!isFormData && { "Content-Type": "application/json" }),
        ...(options.headers || {})
    };
    let res;
    try {
        res = await fetch(url, {
            method: options.method || "GET",
            headers,
            body: options.body
                ? (isFormData ? options.body : JSON.stringify(options.body))
                : undefined
        });
    } catch (networkError) {
        console.error(
            "NETWORK ERROR:",
            networkError
        );
        showToast("Network error. Please check your connection.", "danger");
        throw networkError;
    }
    if (res.status === 401 && !endpoint.includes("/auth/login")) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("client_id");
        if (!window.location.pathname.includes("login")) {
            window.location.href = "/login";
        }
        const error = new Error("Unauthorized");
        error.status = 401;
        throw error;
    }
    if (options.responseType === "blob") {
        if (!res.ok) {
            const errorText = await res.text();
            let message = "Download failed";
            try {
                const errJson = JSON.parse(errorText);
                message = errJson.detail || message;
            } catch {
                message = errorText || message;
            }
            showToast(message, "danger");
            const error = new Error(message);
            error.status = res.status;
            throw error;
        }
        return await res.blob();
    }
    const rawText = await res.text();
    let data;
    try {
        data = rawText ? JSON.parse(rawText) : null;
    } catch {
        data = { detail: rawText };
    }
        if (!res.ok) {
            let message = data?.detail || "API Error";
            if (typeof message !== "string") {
                if (Array.isArray(message)) {
                    message = message.map(m => m.msg || JSON.stringify(m)).join(", ");
                } else if (typeof message === "object") {
                    message = message.msg || JSON.stringify(message);
                } else {
                    message = String(message);
                }
            }
            showToast(message, "danger");
            const error = new Error(message);
            error.response = data;
            error.status = res.status;
            throw error;
        }
    return data;
}