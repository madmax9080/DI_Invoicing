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
        // error handled by apiFetch
    }
}

async function submitDraft(invoiceId) {
    try {
        const invoice = pendingInvoices.find(item => item.id === invoiceId);
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

function renderTable() {
    const tbody = document.getElementById("pendingInvoicesTableBody");
    const countEl = document.getElementById("pendingInvoiceCount");
    tbody.innerHTML = "";
    countEl.textContent = `${pendingInvoices.length} drafts`;
    if (!pendingInvoices.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted py-4">
                    No pending invoices found.
                </td>
            </tr>
        `;
        return;
    }
    pendingInvoices.forEach((invoice, index) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>
                <button class="btn btn-outline-danger btn-sm download-draft" data-id="${invoice.id}" data-name="${invoice.buyerBusinessName || "draft"}">
                    <i class="bi bi-file-pdf"></i>
                </button>
                <button class="btn btn-outline-secondary btn-sm delete-draft" data-id="${invoice.id}">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
            <td>${formatDate(invoice.invoiceDate)}</td>
            <td>${invoice.internal_invoice_no || "-"}</td>
            <td>${invoice.invoiceRefNo || "-"}</td>
            <td>${invoice.buyerBusinessName || "-"}</td>
            <td>${invoice.buyerNTNCNIC || "-"}</td>
            <td><span class="badge bg-warning text-dark">${invoice.status}</span></td>
            <td>${formatDate(invoice.created_at)}</td>
        `;
        tbody.appendChild(row);
    });
}

export async function initPendingInvoices() {
    await loadPendingInvoices();
    document
        .getElementById("pendingInvoicesTableBody")
        .addEventListener("click", async (event) => {
            const button = event.target.closest("button");
            if (!button) return;
            if (button.classList.contains("download-draft")) {
                const id = button.dataset.id;
                const name = button.dataset.name;
                await downloadDraft(id, name);
            }
            if (button.classList.contains("delete-draft")) {
                const id = button.dataset.id;
                await deleteDraft(id);
            }
        });
}

export function destroyPendingInvoices() {
    const tbody = document.getElementById("pendingInvoicesTableBody");
    if (tbody) {
        tbody.replaceWith(tbody.cloneNode(false));
    }
}
