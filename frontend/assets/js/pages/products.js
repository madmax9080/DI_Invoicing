import { apiFetch } from "../api.js";
import { showToast } from "../toast.js";

const EVENTS_NS = ".products";
let products = [];
let editingProductId = null;

export async function initProducts() {
    bindEvents();
    await loadProducts();
}

export function destroyProducts() {
    $("#productForm").off(EVENTS_NS);
    $("#productSearchInput").off(EVENTS_NS);
    $(document).off(EVENTS_NS);
    products = [];
    editingProductId = null;
}

function bindEvents() {
    $("#productForm")
        .off(EVENTS_NS)
        .on(`submit${EVENTS_NS}`, saveProduct);
    $("#productSearchInput")
        .off(EVENTS_NS)
        .on(`input${EVENTS_NS}`, renderProducts);
    $("#cancelProductEditBtn")
        .off(EVENTS_NS)
        .on(`click${EVENTS_NS}`, resetProductForm);
    $(document)
        .off(`click${EVENTS_NS}`, ".edit-product-btn")
        .on(`click${EVENTS_NS}`, ".edit-product-btn", function () {
            editProduct(Number($(this).data("id")));
        });
    $(document)
        .off(`click${EVENTS_NS}`, ".delete-product-btn")
        .on(`click${EVENTS_NS}`, ".delete-product-btn", async function () {
            const product = products.find(
                item => item.id === Number($(this).data("id"))
            );
            if (!product || !window.confirm(`Delete "${product.name}"?`)) {
                return;
            }
            try {
                await apiFetch(
                    `/products/${product.id}`,
                    { method: "DELETE" }
                );
                showToast("Product deleted.", "success");
                await loadProducts();
            } catch (error) {
                console.error("Product deletion failed:", error);
            }
        });
}

async function loadProducts() {
    try {
        products = await apiFetch("/products/");
        renderProducts();
    } catch (error) {
        console.error("Failed to load products:", error);
        $("#productsTableBody").html(
            '<tr><td colspan="4" class="text-center text-danger">Unable to load products.</td></tr>'
        );
    }
}

async function saveProduct(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) {
        return;
    }
    const payload = {
        name: $("#productNameInput").val().trim(),
        hs_code: $("#productHsCodeInput").val().trim() || null,
        stock_quantity: Number($("#productStockInput").val())
    };
    const $button = $("#saveProductBtn");
    $button.prop("disabled", true);
    try {
        const endpoint = editingProductId
            ? `/products/${editingProductId}`
            : "/products/";
        await apiFetch(endpoint, {
            method: editingProductId ? "PUT" : "POST",
            body: payload
        });
        showToast(
            editingProductId
                ? "Product updated."
                : "Product added.",
            "success"
        );
        resetProductForm();
        await loadProducts();
    } catch (error) {
        console.error("Product save failed:", error);
    } finally {
        $button.prop("disabled", false);
    }
}

function editProduct(productId) {
    const product = products.find(item => item.id === productId);
    if (!product) {
        return;
    }
    editingProductId = product.id;
    $("#productFormTitle").text("Edit product");
    $("#productNameInput").val(product.name);
    $("#productHsCodeInput").val(product.hs_code || "");
    $("#productStockInput").val(product.stock_quantity);
    $("#saveProductBtn").text("Update product");
    $("#cancelProductEditBtn").removeClass("d-none");
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetProductForm() {
    editingProductId = null;
    $("#productForm")[0].reset();
    $("#productFormTitle").text("Add product");
    $("#saveProductBtn").text("Save product");
    $("#cancelProductEditBtn").addClass("d-none");
}

function renderProducts() {
    const search = $("#productSearchInput").val().trim().toLowerCase();
    const filtered = products.filter(product =>
        `${product.name} ${product.hs_code || ""}`
            .toLowerCase()
            .includes(search)
    );
    if (!filtered.length) {
        $("#productsTableBody").html(
            '<tr><td colspan="4" class="text-center text-muted">No products found.</td></tr>'
        );
        return;
    }
    $("#productsTableBody").html(filtered.map(product => `
        <tr>
            <td class="fw-semibold">${escapeHtml(product.name)}</td>
            <td>${escapeHtml(product.hs_code || "-")}</td>
            <td class="text-end">${formatNumber(product.stock_quantity)}</td>
            <td>
                <div class="d-flex gap-1">
                    <button class="btn btn-sm btn-outline-primary edit-product-btn" data-id="${product.id}" type="button" title="Edit product and stock">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-product-btn" data-id="${product.id}" type="button" title="Delete product">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join(""));
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString(undefined, {
        maximumFractionDigits: 4
    });
}
