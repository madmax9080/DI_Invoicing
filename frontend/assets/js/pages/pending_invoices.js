import { apiFetch } from "../api.js";
import { showToast } from "../toast.js";

let pendingInvoices = [];

function formatDate(value) {
    if (!value) return "-";
    return new Date(value).toLocaleDateString();
}

function downloadFile(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}

async function loadPendingInvoices() {
    try {
        const data = await apiFetch("/invoices/?status=pending");
        pendingInvoices = Array.isArray(data) ? data : [];
        renderTable();
    } catch (err) {
        console.error("Failed to load pending invoices", err);
    }
}

async function downloadDraft(invoiceId, buyerBusinessName) {
    try {
        const blob = await apiFetch(
            `/reports/pdf/${invoiceId}`,
            { responseType: "blob" }
        );
        downloadFile(blob, `${buyerBusinessName || "invoice"}.pdf`);
    } catch (err) {
    }
}

async function submitDraft(invoiceId) {
    try {
        const invoice = pendingInvoices.find(item => item.id === invoiceId);
        console.log(invoice);
        if (!invoice) {
            return;
        }
        const payload = {
            internalInvoiceNo: invoice.internal_invoice_no,
            invoiceType: invoice.invoiceType,
            invoiceDate: invoice.invoiceDate,
            invoiceRefNo: invoice.invoiceRefNo || "",
            sellerNTNCNIC: invoice.sellerNTNCNIC,
            sellerBusinessName: invoice.sellerBusinessName,
            sellerProvince: invoice.sellerProvince,
            sellerAddress: invoice.sellerAddress,
            buyerNTNCNIC: invoice.buyerNTNCNIC,
            buyerBusinessName: invoice.buyerBusinessName,
            buyerProvince: invoice.buyerProvince,
            buyerAddress: invoice.buyerAddress,
            buyerRegistrationType: invoice.buyerRegistrationType,
            items: (invoice.items || []).map(item => ({
                hsCode: item.hsCode,
                productDescription: item.productDescription,
                rate: item.rate,
                itemRate: Number(item.itemRate) || 0,
                uoM: item.uom,
                quantity: item.quantity,
                valueSalesExcludingST: item.valueSalesExcludingST,
                salesTaxApplicable: item.salesTaxApplicable,
                totalValues: item.totalValues,
                fixedNotifiedValueOrRetailPrice: item.fixedNotifiedValueOrRetailPrice,
                salesTaxWithheldAtSource: item.salesTaxWithheldAtSource,
                furtherTax: item.furtherTax,
                extraTax: item.extraTax,
                fedPayable: item.fedPayable,
                discount: item.discount,
                tax236HRate: item.tax236HRate,
                tax236H: item.tax236H,
                saleType: item.saleType,
                sroScheduleNo: item.sroScheduleNo,
                sroItemSerialNo: item.sroItemSerialNo
            }))
        };
        const response = await apiFetch("/invoices/post", {
            method: "POST",
            body: payload
        });
        if (response?.status === "success") {
            showToast(`Invoice submitted successfully. FBR No: ${response.fbrInvoiceNumber}`, "success", "Invoice Submitted");
            await loadPendingInvoices();
            return;
        }
        if (response?.status === "invalid") {
            const validation = response?.fbr_response?.validationResponse || {};
            showToast(validation.error || "Invoice rejected by FBR", "danger", "Submission Failed");
            return;
        }
        if (response?.status === "already_posted") {
            showToast(`Invoice already posted with FBR No: ${response.fbrInvoiceNumber}`, "warning", "Duplicate");
            await loadPendingInvoices();
        }
    } catch (err) {
        showToast(err.message || "Submission failed", "danger", "Submission Failed");
    }
}

async function editDraft(invoiceId) {
    const invoice = pendingInvoices.find(i => i.id === invoiceId);
    if (!invoice) {
        showToast("Invoice not found", "warning");
        return;
    }
    console.log("Invoice object:", invoice);
    sessionStorage.setItem(
        "editingInvoice",
        JSON.stringify(invoice)
    );
    window.location.hash = "#create-invoice";
}

async function deleteDraft(invoiceId) {
    if (!confirm("Delete this draft invoice?")) {
        return;
    }
    try {
        await apiFetch(`/invoices/${invoiceId}`, {
            method: "DELETE"
        });
        showToast("Draft invoice deleted", "success");
        await loadPendingInvoices();
    } catch (err) {
        showToast(err.message || "Delete failed", "danger");
    }
}

function getTotalQuantity(invoice) {
    return (invoice.items || []).reduce(
        (sum, item) => sum + Number(item.quantity || 0),
        0
    );
}

function getTaxableValue(invoice) {
    return (invoice.items || []).reduce(
        (sum, item) => sum + Number(item.valueSalesExcludingST || 0),
        0
    ).toFixed(2);
}

function getSalesTax(invoice) {
    return (invoice.items || []).reduce(
        (sum, item) => sum + Number(item.salesTaxApplicable || 0),
        0
    ).toFixed(2);
}

function getGrandTotal(invoice) {
    return (invoice.items || []).reduce(
        (sum, item) => sum + Number(item.totalValues || 0),
        0
    ).toFixed(2);
}

function renderTable() {
    const tbody = document.getElementById("pendingInvoicesTableBody");
    const countEl = document.getElementById("pendingInvoiceCount");
    tbody.innerHTML = "";
    const totalItems = pendingInvoices.reduce(
        (sum, invoice) => sum + (invoice.items?.length || 0),
        0
    );
    countEl.textContent = `${pendingInvoices.length} drafts (${totalItems} items)`;
    if (!pendingInvoices.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="22" class="text-center text-muted py-4">
                    No pending invoices found.
                </td>
            </tr>
        `;
        return;
    }
    let rowNo = 1;
    pendingInvoices.forEach(invoice => {
        if (!invoice.items || invoice.items.length === 0) {
            tbody.innerHTML += `
                <tr>
                    <td>${rowNo++}</td>
                    <td class="text-nowrap">
                        <button
                            class="btn btn-outline-primary btn-sm edit-draft"
                            data-id="${invoice.id}"
                            title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button
                            class="btn btn-outline-success btn-sm submit-draft"
                            data-id="${invoice.id}"
                            title="Submit">
                            <i class="bi bi-send"></i>
                        </button>
                        <button
                            class="btn btn-outline-danger btn-sm download-draft"
                            data-id="${invoice.id}"
                            data-name="${invoice.buyerBusinessName || "draft"}"
                            title="Download PDF">
                            <i class="bi bi-file-pdf"></i>
                        </button>
                        <button
                            class="btn btn-outline-secondary btn-sm delete-draft"
                            data-id="${invoice.id}"
                            title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                    <td>${formatDate(invoice.invoiceDate)}</td>
                    <td>${invoice.internal_invoice_no || "-"}</td>
                    <td>${invoice.buyerBusinessName || "-"}</td>
                    <td colspan="17" class="text-center text-muted">
                        No Items
                    </td>
                </tr>
            `;
            return;
        }
        invoice.items.forEach((item, itemIndex) => {
            tbody.innerHTML += `
                <tr>
                    <td>${rowNo++}</td>
                    <td class="text-nowrap">
                        ${
                            itemIndex === 0
                                ? `
                        <button
                            class="btn btn-outline-primary btn-sm edit-draft"
                            data-id="${invoice.id}"
                            title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button
                            class="btn btn-outline-success btn-sm submit-draft"
                            data-id="${invoice.id}"
                            title="Submit">
                            <i class="bi bi-send"></i>
                        </button>
                        <button
                            class="btn btn-outline-danger btn-sm download-draft"
                            data-id="${invoice.id}"
                            data-name="${invoice.buyerBusinessName || "draft"}"
                            title="Download PDF">
                            <i class="bi bi-file-pdf"></i>
                        </button>
                        <button
                            class="btn btn-outline-secondary btn-sm delete-draft"
                            data-id="${invoice.id}"
                            title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                        `
                                : ""
                        }
                    </td>
                    <td>${formatDate(invoice.invoiceDate)}</td>
                    <td>${invoice.internal_invoice_no || "-"}</td>
                    <td>${invoice.buyerBusinessName || "-"}</td>
                    <td>${item.hsCode || "-"}</td>
                    <td>${item.productDescription || "-"}</td>
                    <td>${item.saleType || "-"}</td>
                    <td class="text-end">${Number(item.quantity || 0).toFixed(2)}</td>
                    <td>${item.uom || "-"}</td>
                    <td class="text-end">${item.rate || "-"}</td>
                    <td class="text-end">
                        ${Number(item.itemRate)}
                    </td>
                    <td class="text-end">${Number(item.valueSalesExcludingST || 0).toFixed(2)}</td>
                    <td class="text-end">${Number(item.fixedNotifiedValueOrRetailPrice || 0).toFixed(2)}</td>
                    <td class="text-end">${Number(item.salesTaxApplicable || 0).toFixed(2)}</td>
                    <td class="text-end">${Number(item.furtherTax || 0).toFixed(2)}</td>
                    <td class="text-end">${Number(item.fedPayable || 0).toFixed(2)}</td>
                    <td class="text-end">${Number(item.salesTaxWithheldAtSource || 0).toFixed(2)}</td>
                    <td class="text-end">
                        ${
                            item.extraTax === "" ||
                            item.extraTax === null ||
                            item.extraTax === undefined
                                ? "-"
                                : Number(item.extraTax).toFixed(2)
                        }
                    </td>
                    <td>
                        ${
                            Number(item.tax236HRate || 0) > 0
                                ? `${Number(item.tax236HRate).toFixed(2)}%<br><small>${Number(item.tax236H || 0).toFixed(2)}</small>`
                                : "-"
                        }
                    </td>
                    <td class="text-end">${Number(item.discount || 0).toFixed(2)}</td>
                    <td class="text-end fw-semibold">${Number(item.totalValues || 0).toFixed(2)}</td>
                    <td>${item.sroScheduleNo || "-"}</td>
                    <td>${item.sroItemSerialNo || "-"}</td>
                </tr>
            `;
        });
    });
}

function renderItemsTable(invoice) {
    const tbody = document.getElementById("pendingInvoiceItemsBody");
    tbody.innerHTML = "";
    if (!invoice.items?.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="18" class="text-center text-muted">
                    No items found.
                </td>
            </tr>
        `;
        return;
    }
    invoice.items.forEach((item, index) => {
        tbody.insertAdjacentHTML(
            "beforeend",
            buildPendingItemRow(item, index)
        );
    });
}

export async function initPendingInvoices() {
    await loadPendingInvoices();
    document
    .getElementById("pendingInvoicesTableBody")
    .addEventListener("click", async (event) => {
        const button = event.target.closest("button");
        if (!button) return;
        const id = Number(button.dataset.id);
        if (button.classList.contains("download-draft")) {
            await downloadDraft(id, button.dataset.name);
            return;
        }
        if (button.classList.contains("submit-draft")) {
            await submitDraft(id);
            return;
        }
        if (button.classList.contains("edit-draft")) {
            await editDraft(id);
            return;
        }
        if (button.classList.contains("delete-draft")) {
            await deleteDraft(id);
            return;
        }
    });
}

export function destroyPendingInvoices() {
    const tbody = document.getElementById("pendingInvoicesTableBody");
    if (tbody) {
        tbody.replaceWith(tbody.cloneNode(false));
    }
}