import { apiFetch } from "../api.js";
import { showToast } from "../toast.js";

const EVENTS_NS = ".inventory";
let products = [];
let boms = [];
let nextLineId = 0;

export async function initInventory() {
    bindEvents();
    const today = localDateString(new Date());
    $("#purchaseDate, #productionDate").val(today);
    await refreshInventoryData();
    addPurchaseLine();
}

export function destroyInventory() {
    $("#purchaseForm, #bomForm, #productionForm").off(EVENTS_NS);
    $("#addPurchaseLineBtn, #addBomLineBtn").off(EVENTS_NS);
    $("#purchaseLines, #bomLines, #bomHistoryBody").off(EVENTS_NS);
    $("#bomFinishedProduct, #productionFinishedProduct, #productionQuantity").off(EVENTS_NS);
    $(".inventory-tabs").off(EVENTS_NS);
    products = [];
    boms = [];
}

function bindEvents() {
    $(".inventory-tabs")
        .off(EVENTS_NS)
        .on(`click${EVENTS_NS}`, "[data-inventory-tab]", function () {
            const tab = $(this).data("inventory-tab");
            $(".inventory-tabs [data-inventory-tab]").removeClass("active");
            $(this).addClass("active");
            $(".inventory-pane").addClass("d-none");
            $(`[data-inventory-pane="${tab}"]`).removeClass("d-none");
        });
    $("#addPurchaseLineBtn")
        .off(EVENTS_NS)
        .on(`click${EVENTS_NS}`, addPurchaseLine);
    $("#addBomLineBtn")
        .off(EVENTS_NS)
        .on(`click${EVENTS_NS}`, addBomLine);
    $("#purchaseLines")
        .off(EVENTS_NS)
        .on(`click${EVENTS_NS}`, ".remove-inventory-line", function () {
            $(this).closest(".inventory-line").remove();
            if (!$("#purchaseLines .inventory-line").length) addPurchaseLine();
        });
    $("#bomLines")
        .off(EVENTS_NS)
        .on(`click${EVENTS_NS}`, ".remove-inventory-line", function () {
            $(this).closest(".inventory-line").remove();
            if (!$("#bomLines .inventory-line").length) addBomLine();
        });
    $("#bomFinishedProduct")
        .off(EVENTS_NS)
        .on(`change${EVENTS_NS}`, loadSelectedBOM);
    $("#productionFinishedProduct, #productionQuantity")
        .off(EVENTS_NS)
        .on(`change${EVENTS_NS} input${EVENTS_NS}`, renderProductionPreview);
    $("#purchaseForm")
        .off(EVENTS_NS)
        .on(`submit${EVENTS_NS}`, savePurchase);
    $("#bomForm")
        .off(EVENTS_NS)
        .on(`submit${EVENTS_NS}`, saveBOM);
    $("#productionForm")
        .off(EVENTS_NS)
        .on(`submit${EVENTS_NS}`, saveProduction);
    $("#bomHistoryBody")
        .off(EVENTS_NS)
        .on(`click${EVENTS_NS}`, "[data-edit-bom]", function () {
            $("#bomFinishedProduct").val(String($(this).data("edit-bom"))).trigger("change");
            $(".inventory-tabs [data-inventory-tab='boms']").trigger("click");
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
}

async function refreshInventoryData() {
    const clientId = localStorage.getItem("client_id");
    if (!clientId) {
        throw new Error("Select a business before using inventory.");
    }
    const [loadedProducts, loadedBoms, purchases, productionOrders, movements] =
        await Promise.all([
            apiFetch("/products/"),
            apiFetch("/inventory/boms"),
            apiFetch("/inventory/purchases?limit=50"),
            apiFetch("/inventory/production-orders?limit=50"),
            apiFetch("/inventory/movements?limit=100")
        ]);
    products = loadedProducts;
    boms = loadedBoms;
    renderProductOptions();
    renderPurchaseHistory(purchases);
    renderBOMHistory();
    renderProductionHistory(productionOrders);
    renderMovements(movements);
    loadSelectedBOM();
    renderProductionPreview();
}

function renderProductOptions() {
    const previousBOMProduct = $("#bomFinishedProduct").val();
    const previousProductionProduct = $("#productionFinishedProduct").val();
    $("#bomFinishedProduct").html(
        productOptions("finished_good", "Select a finished good")
    );
    $("#productionFinishedProduct").html(
        productOptions("finished_good", "Select a finished good")
    );
    if (products.some(product => String(product.id) === previousBOMProduct && product.product_type === "finished_good")) {
        $("#bomFinishedProduct").val(previousBOMProduct);
    }
    if (products.some(product => String(product.id) === previousProductionProduct && product.product_type === "finished_good")) {
        $("#productionFinishedProduct").val(previousProductionProduct);
    }
}

function productOptions(type, placeholder) {
    const available = products
        .filter(product => !type || product.product_type === type)
        .sort((left, right) => left.name.localeCompare(right.name));
    return [
        `<option value="">${escapeHtml(placeholder)}</option>`,
        ...available.map(product =>
            `<option value="${product.id}">${escapeHtml(product.name)} (${formatNumber(product.stock_quantity)} ${escapeHtml(product.uom || "unit")})</option>`
        )
    ].join("");
}

function addPurchaseLine(productId = "", quantity = "", unitCost = "") {
    const id = ++nextLineId;
    $("#purchaseLines").append(`
        <div class="inventory-line" data-line-id="${id}">
            <div>
                <label for="purchaseProduct${id}">Product</label>
                <select id="purchaseProduct${id}" class="form-select donezo-input inventory-product" required>
                    ${productOptions(null, "Select a product")}
                </select>
            </div>
            <div>
                <label for="purchaseQuantity${id}">Quantity received</label>
                <input id="purchaseQuantity${id}" type="number" min="0.0001" step="0.0001" class="form-control donezo-input inventory-quantity" value="${escapeHtml(quantity)}" required>
            </div>
            <div>
                <label for="purchaseCost${id}">Unit cost</label>
                <input id="purchaseCost${id}" type="number" min="0" step="0.0001" class="form-control donezo-input inventory-unit-cost" value="${escapeHtml(unitCost)}">
            </div>
            <button type="button" class="btn btn-outline-danger remove-inventory-line" aria-label="Remove item" title="Remove item"><i class="bi bi-x-lg"></i></button>
        </div>
    `);
    if (productId) $(`#purchaseProduct${id}`).val(String(productId));
}

function addBomLine(productId = "", quantity = "") {
    const id = ++nextLineId;
    $("#bomLines").append(`
        <div class="inventory-line bom-line" data-line-id="${id}">
            <div>
                <label for="bomComponent${id}">Raw material</label>
                <select id="bomComponent${id}" class="form-select donezo-input bom-component" required>
                    ${productOptions("raw_material", "Select a raw material")}
                </select>
            </div>
            <div>
                <label for="bomQuantity${id}">Quantity per finished unit</label>
                <input id="bomQuantity${id}" type="number" min="0.0001" step="0.0001" class="form-control donezo-input bom-quantity" value="${escapeHtml(quantity)}" required>
            </div>
            <button type="button" class="btn btn-outline-danger remove-inventory-line" aria-label="Remove component" title="Remove component"><i class="bi bi-x-lg"></i></button>
        </div>
    `);
    if (productId) $(`#bomComponent${id}`).val(String(productId));
}

function loadSelectedBOM() {
    const finishedProductId = Number($("#bomFinishedProduct").val());
    const bom = boms.find(item => item.finished_product_id === finishedProductId);
    $("#bomLines").empty();
    if (!bom) {
        addBomLine();
        return;
    }
    bom.components.forEach(component =>
        addBomLine(component.component_product_id, component.quantity_per_unit)
    );
}

async function savePurchase(event) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    const items = $("#purchaseLines .inventory-line").map(function () {
        return {
            product_id: Number($(this).find(".inventory-product").val()),
            quantity: $(this).find(".inventory-quantity").val(),
            unit_cost: $(this).find(".inventory-unit-cost").val() || "0"
        };
    }).get();
    await withDisabledButton("#savePurchaseBtn", async () => {
        await apiFetch("/inventory/purchases", {
            method: "POST",
            body: {
                supplier_name: $("#purchaseSupplierName").val().trim(),
                supplier_reference: $("#purchaseReference").val().trim() || null,
                received_date: $("#purchaseDate").val(),
                notes: $("#purchaseNotes").val().trim() || null,
                items
            }
        });
        showToast("Purchase receipt saved and stock updated.", "success");
        $("#purchaseForm")[0].reset();
        $("#purchaseDate").val(localDateString(new Date()));
        $("#purchaseLines").empty();
        addPurchaseLine();
        await refreshInventoryData();
    });
}

async function saveBOM(event) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    const components = $("#bomLines .inventory-line").map(function () {
        return {
            component_product_id: Number($(this).find(".bom-component").val()),
            quantity_per_unit: $(this).find(".bom-quantity").val()
        };
    }).get();
    await withDisabledButton("#saveBomBtn", async () => {
        await apiFetch("/inventory/boms", {
            method: "POST",
            body: {
                finished_product_id: Number($("#bomFinishedProduct").val()),
                components
            }
        });
        showToast("Bill of materials saved.", "success");
        await refreshInventoryData();
    });
}

async function saveProduction(event) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    await withDisabledButton("#saveProductionBtn", async () => {
        await apiFetch("/inventory/production-orders", {
            method: "POST",
            body: {
                finished_product_id: Number($("#productionFinishedProduct").val()),
                quantity_produced: $("#productionQuantity").val(),
                produced_date: $("#productionDate").val(),
                notes: $("#productionNotes").val().trim() || null
            }
        });
        showToast("Production posted; material and finished stock updated.", "success");
        $("#productionForm")[0].reset();
        $("#productionDate").val(localDateString(new Date()));
        await refreshInventoryData();
    });
}

function renderProductionPreview() {
    const productId = Number($("#productionFinishedProduct").val());
    const bom = boms.find(item => item.finished_product_id === productId);
    if (!bom) {
        $("#productionBomSummary").text("Select a finished good with a saved recipe.");
        $("#saveProductionBtn").prop("disabled", true);
        return;
    }
    const quantity = Number($("#productionQuantity").val()) || 0;
    const parts = bom.components.map(component => {
        const exactAmount = component.quantity_per_unit * quantity;
        const amount = Math.ceil(exactAmount * 10000 - 1e-9) / 10000;
        const product = products.find(item => item.id === component.component_product_id);
        return `${formatNumber(amount)} ${escapeHtml(component.component_uom)} ${escapeHtml(component.component_product_name)}${product && amount > Number(product.stock_quantity) ? " (insufficient stock)" : ""}`;
    });
    $("#productionBomSummary").html(
        quantity > 0
            ? `<strong>Materials to consume:</strong> ${parts.join("; ")}`
            : `<strong>Recipe:</strong> ${parts.join("; ")} per finished unit`
    );
    $("#saveProductionBtn").prop("disabled", false);
}

function renderPurchaseHistory(receipts) {
    if (!receipts.length) {
        $("#purchaseHistoryBody").html('<tr><td colspan="5" class="text-center text-muted">No purchase receipts yet.</td></tr>');
        return;
    }
    $("#purchaseHistoryBody").html(receipts.map(receipt => {
        const total = receipt.items.reduce(
            (sum, item) => sum + Number(item.quantity) * Number(item.unit_cost),
            0
        );
        return `<tr>
            <td>${escapeHtml(receipt.received_date)}</td>
            <td class="fw-semibold">${escapeHtml(receipt.supplier_name)}</td>
            <td>${escapeHtml(receipt.supplier_reference || "-")}</td>
            <td>${receipt.items.map(item => `${escapeHtml(item.product_name)}: ${formatNumber(item.quantity)} ${escapeHtml(item.uom)}`).join("<br>")}</td>
            <td class="text-end">${formatMoney(total)}</td>
        </tr>`;
    }).join(""));
}

function renderBOMHistory() {
    if (!boms.length) {
        $("#bomHistoryBody").html('<tr><td colspan="2" class="text-center text-muted">No recipes saved yet.</td></tr>');
        return;
    }
    $("#bomHistoryBody").html(boms.map(bom => `
        <tr>
            <td class="fw-semibold">${escapeHtml(bom.finished_product_name)}</td>
            <td>
                ${bom.components.map(component =>
        `${formatNumber(component.quantity_per_unit)} ${escapeHtml(component.component_uom)} ${escapeHtml(component.component_product_name)}`
    ).join("<br>")}
                <button class="btn btn-sm btn-outline-primary mt-2" type="button" data-edit-bom="${bom.finished_product_id}">Edit recipe</button>
            </td>
        </tr>
    `).join(""));
}

function renderProductionHistory(orders) {
    if (!orders.length) {
        $("#productionHistoryBody").html('<tr><td colspan="4" class="text-center text-muted">No production recorded yet.</td></tr>');
        return;
    }
    $("#productionHistoryBody").html(orders.map(order => `
        <tr>
            <td>${escapeHtml(order.produced_date)}</td>
            <td class="fw-semibold">${escapeHtml(order.finished_product_name)}</td>
            <td class="text-end">${formatNumber(order.quantity_produced)} ${escapeHtml(order.finished_product_uom)}</td>
            <td>${order.components.map(component =>
        `${formatNumber(component.quantity_consumed)} ${escapeHtml(component.uom)} ${escapeHtml(component.product_name)}`
    ).join("<br>")}</td>
        </tr>
    `).join(""));
}

function renderMovements(movements) {
    if (!movements.length) {
        $("#inventoryMovementsBody").html('<tr><td colspan="6" class="text-center text-muted">No stock movements yet.</td></tr>');
        return;
    }
    $("#inventoryMovementsBody").html(movements.map(movement => {
        const quantity = Number(movement.quantity);
        const reference = movement.reference_type
            ? `${formatMovementType(movement.reference_type)} #${movement.reference_id || ""}`
            : "-";
        return `<tr>
            <td>${escapeHtml(movement.movement_date)}</td>
            <td class="fw-semibold">${escapeHtml(movement.product_name)}</td>
            <td>${escapeHtml(formatMovementType(movement.movement_type))}</td>
            <td class="text-end ${quantity < 0 ? "text-danger" : "text-success"}">${quantity > 0 ? "+" : ""}${formatNumber(quantity)} ${escapeHtml(movement.uom)}</td>
            <td>${escapeHtml(reference)}</td>
            <td>${escapeHtml(movement.notes || "-")}</td>
        </tr>`;
    }).join(""));
}

function formatMovementType(type) {
    return {
        opening_balance: "Opening balance",
        purchase_receipt: "Purchase receipt",
        production_consumption: "Production consumption",
        production_output: "Production output",
        sale: "Sale",
        sale_reversal: "Sale reversal",
        adjustment: "Adjustment"
    }[type] || type;
}

async function withDisabledButton(selector, action) {
    const button = $(selector);
    const wasDisabled = button.prop("disabled");
    button.prop("disabled", true);
    try {
        await action();
    } catch (error) {
        console.error("Inventory action failed:", error);
    } finally {
        button.prop("disabled", wasDisabled);
    }
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString(undefined, {
        maximumFractionDigits: 4
    });
}

function formatMoney(value) {
    return Number(value || 0).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function localDateString(value) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}
