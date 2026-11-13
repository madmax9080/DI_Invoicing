import { apiFetch } from "../api.js";
import { showToast } from "../toast.js";

let currentLedger = null;
let editingReceiptId = null;
const LEDGER_START_DATE = "2026-07-01";

export async function initBuyerLedger() {
    $("#ledgerApplyBtn").on("click", loadBuyerLedger);
    $("#ledgerExportBtn").on("click", () => exportBuyerLedger("excel"));
    $("#ledgerPdfExportBtn").on("click", () => exportBuyerLedger("pdf"));
    $("#editOpeningBalanceBtn").on("click", openOpeningBalanceForm);
    $("#ledgerOpeningBalanceForm").on("submit", saveOpeningBalance);
    $("#ledgerReceiptBtn").on("click", openReceiptForm);
    $("#ledgerReceiptForm").on("submit", saveBuyerReceipt);
    $("#buyerLedgerTableBody")
        .on("click.buyerLedger", ".ledger-receipt-edit", openReceiptEdit)
        .on("click.buyerLedger", ".ledger-receipt-delete", deleteBuyerReceipt);
    $("#ledgerBuyerSelect, #ledgerDateFrom, #ledgerDateTo").on(
        "change",
        invalidateLedger
    );
    $("#ledgerReceiptDate")
        .attr("min", LEDGER_START_DATE)
        .val(localDateString(new Date()));
    await loadLedgerBuyers();
}

export function destroyBuyerLedger() {
    const receiptModal = document.getElementById("ledgerReceiptModal");
    const modalInstance = bootstrap.Modal.getInstance(receiptModal);
    if (modalInstance) modalInstance.hide();
    const openingBalanceModal = document.getElementById("ledgerOpeningBalanceModal");
    const openingBalanceModalInstance = bootstrap.Modal.getInstance(openingBalanceModal);
    if (openingBalanceModalInstance) openingBalanceModalInstance.hide();
    $("#ledgerApplyBtn").off("click");
    $("#ledgerExportBtn").off("click");
    $("#ledgerPdfExportBtn").off("click");
    $("#editOpeningBalanceBtn").off("click");
    $("#ledgerOpeningBalanceForm").off("submit");
    $("#ledgerReceiptBtn").off("click");
    $("#ledgerReceiptForm").off("submit");
    $("#buyerLedgerTableBody").off(".buyerLedger");
    $("#ledgerBuyerSelect, #ledgerDateFrom, #ledgerDateTo").off("change");
}

function invalidateLedger() {
    currentLedger = null;
    $("#ledgerExportBtn").prop("disabled", true);
    $("#ledgerPdfExportBtn").prop("disabled", true);
    $("#ledgerReceiptBtn").prop("disabled", !$("#ledgerBuyerSelect").val());
}

async function loadLedgerBuyers() {
    invalidateLedger();
    const select = $("#ledgerBuyerSelect");
    const selectedId = select.val();
    const params = new URLSearchParams({ limit: "100" });
    const result = await apiFetch(`/buyer-ledger/buyers?${params}`);
    const buyers = [...result.items];
    while (buyers.length < result.total) {
        params.set("skip", String(buyers.length));
        const page = await apiFetch(`/buyer-ledger/buyers?${params}`);
        if (!page.items.length) break;
        buyers.push(...page.items);
    }
    select.empty().append('<option value="">Select a buyer</option>');
    buyers.forEach(buyer => {
        const label = buyer.ntn_cnic
            ? `${buyer.name} (${buyer.ntn_cnic})`
            : buyer.name;
        select.append($("<option>", { value: buyer.id, text: label })
            .data("openingBalance", buyer.opening_balance));
    });
    if (selectedId && select.find(`option[value="${selectedId}"]`).length) {
        select.val(selectedId);
    }
    invalidateLedger();
    $("#ledgerStatus").text(`${buyers.length} buyer${buyers.length === 1 ? "" : "s"} found.`);
}

async function loadBuyerLedger() {
    invalidateLedger();
    const buyerId = $("#ledgerBuyerSelect").val();
    $("#ledgerReceiptBuyer").text(
        $("#ledgerBuyerSelect option:selected").text()
    );
    if (!buyerId) {
        $("#ledgerStatus").text("Select a buyer before loading the ledger.");
        $("#ledgerExportBtn").prop("disabled", true);
        $("#ledgerPdfExportBtn").prop("disabled", true);
        return;
    }
    const fromDate = $("#ledgerDateFrom").val();
    const toDate = $("#ledgerDateTo").val();
    if (
        (fromDate && fromDate < LEDGER_START_DATE)
        || (toDate && toDate < LEDGER_START_DATE)
    ) {
        $("#ledgerStatus").text(
            "Buyer ledger history starts on July 1, 2026 (FY 2026-2027)."
        );
        return;
    }
    if (fromDate && toDate && fromDate > toDate) {
        $("#ledgerStatus").text("From date must be on or before to date.");
        return;
    }

    const params = new URLSearchParams();
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    const query = params.toString();
    const result = await apiFetch(
        `/buyer-ledger/${buyerId}${query ? `?${query}` : ""}`
    );
    currentLedger = { buyerId, fromDate, toDate };
    $("#ledgerOpeningBalance").text(formatCurrency(result.opening_balance));
    $("#ledgerOpeningBalance").data("baseOpeningBalance", result.buyer.opening_balance);
    $("#ledgerClosingBalance").text(formatCurrency(result.closing_balance));
    renderLedgerRows(result.transactions);
    $("#ledgerStatus").text(
        `${result.buyer.name}: ${result.transactions.length} transaction${result.transactions.length === 1 ? "" : "s"}.`
    );
    $("#ledgerExportBtn").prop("disabled", false);
    $("#ledgerPdfExportBtn").prop("disabled", false);
}

function openOpeningBalanceForm() {
    const select = $("#ledgerBuyerSelect");
    const buyerId = select.val();
    if (!buyerId) {
        $("#ledgerStatus").text("Select a buyer before editing the opening balance.");
        return;
    }
    const selectedOption = select.find("option:selected");
    $("#ledgerOpeningBalanceBuyer").text(selectedOption.text());
    $("#ledgerOpeningBalanceInput").val(
        Number(selectedOption.data("openingBalance") ?? 0).toFixed(2)
    );
    bootstrap.Modal.getOrCreateInstance(
        document.getElementById("ledgerOpeningBalanceModal")
    ).show();
}

async function saveOpeningBalance(event) {
    event.preventDefault();
    const buyerId = $("#ledgerBuyerSelect").val();
    const openingBalance = $("#ledgerOpeningBalanceInput").val();
    if (!buyerId || openingBalance === "" || !Number.isFinite(Number(openingBalance))) {
        $("#ledgerStatus").text("Enter a valid opening balance for the selected buyer.");
        return;
    }

    const saveButton = $("#ledgerOpeningBalanceSaveBtn").prop("disabled", true);
    try {
        const result = await apiFetch(`/buyer-ledger/${buyerId}/opening-balance`, {
            method: "PUT",
            body: { opening_balance: openingBalance }
        });
        $("#ledgerBuyerSelect option:selected").data(
            "openingBalance",
            result.opening_balance
        );
        bootstrap.Modal.getOrCreateInstance(
            document.getElementById("ledgerOpeningBalanceModal")
        ).hide();
        await loadBuyerLedger();
        showToast("Opening balance updated.", "success");
    } catch (error) {
        $("#ledgerStatus").text(error.message || "Could not update the opening balance.");
    } finally {
        saveButton.prop("disabled", false);
    }
}

function renderLedgerRows(transactions) {
    const body = $("#buyerLedgerTableBody").empty();
    const totals = transactions.reduce((sum, transaction) => ({
        debit: sum.debit + (Number(transaction.debit) || 0),
        credit: sum.credit + (Number(transaction.credit) || 0)
    }), { debit: 0, credit: 0 });
    $("#ledgerDebitTotal").text(formatNumber(totals.debit));
    $("#ledgerCreditTotal").text(formatNumber(totals.credit));
    $("#buyerLedgerTotals").prop("hidden", false);

    if (!transactions.length) {
        body.append(`
            <tr>
                <td colspan="8" class="text-center text-muted py-4">
                    No posted transactions found for this buyer and date range.
                </td>
            </tr>
        `);
        return;
    }

    transactions.forEach(transaction => {
        const row = $("<tr>");
        [
            transaction.date,
            transaction.invoice_type,
            transaction.invoice_number,
            getTransactionDescription(transaction)
        ].forEach(value => row.append($("<td>").text(value)));
        row.append($("<td>", { class: "text-end" }).text(
            transaction.debit ? formatNumber(transaction.debit) : "—"
        ));
        row.append($("<td>", { class: "text-end" }).text(
            transaction.credit ? formatNumber(transaction.credit) : "—"
        ));
        row.append($("<td>", { class: "text-end fw-semibold" }).text(
            formatNumber(transaction.balance)
        ));
        const actions = $("<td>", { class: "text-end text-nowrap" });
        if (transaction.receipt_id) {
            const actionButtons = $("<div>", {
                class: "d-inline-flex align-items-center gap-1"
            });
            actionButtons.append(
                $("<button>", {
                    type: "button",
                    class: "btn btn-sm btn-donezo-secondary ledger-receipt-action ledger-receipt-edit",
                    title: "Edit receipt",
                    "aria-label": "Edit receipt"
                }).append($("<i>", { class: "bi bi-pencil" })).data("receipt", transaction),
                $("<button>", {
                    type: "button",
                    class: "btn btn-sm btn-donezo-secondary ledger-receipt-action ledger-receipt-delete",
                    title: "Delete receipt",
                    "aria-label": "Delete receipt"
                }).append($("<i>", { class: "bi bi-trash" })).data("receiptId", transaction.receipt_id)
            );
            actions.append(actionButtons);
        }
        row.append(actions);
        body.append(row);
    });
}

function getTransactionDescription(transaction) {
    const parts = [];
    if (transaction.notes) parts.push(transaction.notes);
    if (transaction.invoice_type === "Sale Invoice" && !transaction.notes) {
        parts.push("Sale as per invoice");
    }
    if (transaction.payment_method) {
        parts.push(`Payment method: ${transaction.payment_method}`);
    }
    if (transaction.reference_number) {
        parts.push(`Reference: ${transaction.reference_number}`);
    }
    return parts.join(" | ") || "—";
}

async function exportBuyerLedger(format) {
    const ledger = currentLedger;
    if (!ledger) return;
    const params = new URLSearchParams();
    if (ledger.fromDate) params.set("from_date", ledger.fromDate);
    if (ledger.toDate) params.set("to_date", ledger.toDate);
    const query = params.toString();
    const extension = format === "pdf" ? "pdf" : "xlsx";
    try {
        const blob = await apiFetch(
            `/buyer-ledger/${ledger.buyerId}/export/${format}${query ? `?${query}` : ""}`,
            { responseType: "blob" }
        );
        downloadFile(blob, `Buyer_Ledger_${ledger.buyerId}.${extension}`);
    } catch (error) {
        $("#ledgerStatus").text(error.message || `Could not export the buyer ledger as ${format.toUpperCase()}.`);
    }
}

function openReceiptForm() {
    const buyerId = $("#ledgerBuyerSelect").val();
    if (!buyerId) {
        $("#ledgerStatus").text("Select a buyer before recording a receipt.");
        return;
    }
    editingReceiptId = null;
    $("#ledgerReceiptForm")[0].reset();
    $("#ledgerReceiptTitle").text("Record buyer receipt");
    $("#ledgerReceiptSaveBtn").html('<i class="bi bi-check2"></i> Save Receipt');
    $("#ledgerReceiptBuyer").text(
        $("#ledgerBuyerSelect option:selected").text()
    );
    $("#ledgerReceiptDate")
        .attr("min", LEDGER_START_DATE)
        .val(localDateString(new Date()));
    bootstrap.Modal.getOrCreateInstance(
        document.getElementById("ledgerReceiptModal")
    ).show();
}

function openReceiptEdit(event) {
    const receipt = $(event.currentTarget).data("receipt");
    editingReceiptId = receipt.receipt_id;
    $("#ledgerReceiptTitle").text("Edit buyer receipt");
    $("#ledgerReceiptBuyer").text(
        $("#ledgerBuyerSelect option:selected").text()
    );
    $("#ledgerReceiptDate").val(receipt.date);
    $("#ledgerReceiptAmount").val(receipt.credit);
    const description = getTransactionDescription(receipt);
    $("#ledgerReceiptDescription").val(description === "—" ? "" : description);
    $("#ledgerReceiptSaveBtn").html('<i class="bi bi-check2"></i> Update Receipt');
    bootstrap.Modal.getOrCreateInstance(
        document.getElementById("ledgerReceiptModal")
    ).show();
}

async function deleteBuyerReceipt(event) {
    const receiptId = $(event.currentTarget).data("receiptId");
    const buyerId = $("#ledgerBuyerSelect").val();
    if (!buyerId || !window.confirm("Delete this receipt? This will update its invoice allocations and the buyer balance.")) {
        return;
    }
    const deleteButton = $(event.currentTarget).prop("disabled", true);
    try {
        await apiFetch(`/buyer-ledger/${buyerId}/receipts/${receiptId}`, {
            method: "DELETE"
        });
        await loadBuyerLedger();
        showToast("Receipt deleted.", "success");
    } catch (error) {
        $("#ledgerStatus").text(error.message || "Could not delete the receipt.");
        deleteButton.prop("disabled", false);
    }
}

async function saveBuyerReceipt(event) {
    event.preventDefault();
    const buyerId = $("#ledgerBuyerSelect").val();
    const amount = $("#ledgerReceiptAmount").val();
    const receiptDate = $("#ledgerReceiptDate").val();
    if (!buyerId || !receiptDate || !amount || Number(amount) <= 0) {
        $("#ledgerStatus").text("Choose a buyer, date, and positive receipt amount.");
        return;
    }
    if (receiptDate < LEDGER_START_DATE) {
        $("#ledgerStatus").text(
            "Receipts can be recorded from July 1, 2026 onward."
        );
        return;
    }

    const saveButton = $("#ledgerReceiptSaveBtn").prop("disabled", true);
    try {
        const receipt = await apiFetch(
            editingReceiptId
                ? `/buyer-ledger/${buyerId}/receipts/${editingReceiptId}`
                : `/buyer-ledger/${buyerId}/receipts`,
            {
            method: editingReceiptId ? "PUT" : "POST",
            body: {
                received_date: receiptDate,
                amount,
                payment_method: null,
                reference_number: null,
                notes: $("#ledgerReceiptDescription").val().trim() || null
            }
        });
        showToast(editingReceiptId
            ? "Receipt updated and invoice allocations recalculated."
            : `Receipt recorded. Rs. ${formatNumber(receipt.allocated_amount)} allocated to invoices; Rs. ${formatNumber(receipt.unapplied_amount)} remains as buyer credit.`,
        "success");
        bootstrap.Modal.getOrCreateInstance(
            document.getElementById("ledgerReceiptModal")
        ).hide();
        $("#ledgerReceiptForm")[0].reset();
        editingReceiptId = null;
        $("#ledgerReceiptTitle").text("Record buyer receipt");
        $("#ledgerReceiptSaveBtn").html('<i class="bi bi-check2"></i> Save Receipt');
        $("#ledgerReceiptDate")
            .attr("min", LEDGER_START_DATE)
            .val(localDateString(new Date()));
        await loadBuyerLedger();
    } catch (error) {
        $("#ledgerStatus").text(error.message || "Could not save the receipt.");
    } finally {
        saveButton.prop("disabled", false);
    }
}

function formatCurrency(value) {
    return `Rs. ${formatNumber(value)}`;
}

function formatNumber(value) {
    return new Intl.NumberFormat("en-PK", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(Number(value) || 0);
}

function downloadFile(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}

function localDateString(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}
