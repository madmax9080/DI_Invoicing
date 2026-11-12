import { apiFetch } from "../api.js";
import { showToast } from "../toast.js";

let currentLedger = null;
const LEDGER_START_DATE = "2026-07-01";

export async function initBuyerLedger() {
    $("#ledgerApplyBtn").on("click", loadBuyerLedger);
    $("#ledgerExportBtn").on("click", exportBuyerLedger);
    $("#editOpeningBalanceBtn").on("click", openOpeningBalanceForm);
    $("#ledgerOpeningBalanceForm").on("submit", saveOpeningBalance);
    $("#ledgerReceiptBtn").on("click", openReceiptForm);
    $("#ledgerReceiptForm").on("submit", saveBuyerReceipt);
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
    $("#editOpeningBalanceBtn").off("click");
    $("#ledgerOpeningBalanceForm").off("submit");
    $("#ledgerReceiptBtn").off("click");
    $("#ledgerReceiptForm").off("submit");
    $("#ledgerBuyerSelect, #ledgerDateFrom, #ledgerDateTo").off("change");
}

function invalidateLedger() {
    currentLedger = null;
    $("#ledgerExportBtn").prop("disabled", true);
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
    if (!transactions.length) {
        body.append(`
            <tr>
                <td colspan="9" class="text-center text-muted py-4">
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
            transaction.payment_method
                ? `${transaction.invoice_type} (${transaction.payment_method})`
                : transaction.invoice_type,
            transaction.invoice_number,
            transaction.fbr_invoice_number || "—",
            transaction.reference_number || "—",
            transaction.notes || "—"
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
        body.append(row);
    });
}

async function exportBuyerLedger() {
    if (!currentLedger) return;
    const params = new URLSearchParams();
    if (currentLedger.fromDate) params.set("from_date", currentLedger.fromDate);
    if (currentLedger.toDate) params.set("to_date", currentLedger.toDate);
    const query = params.toString();
    const blob = await apiFetch(
        `/buyer-ledger/${currentLedger.buyerId}/export/excel${query ? `?${query}` : ""}`,
        { responseType: "blob" }
    );
    downloadFile(blob, `Buyer_Ledger_${currentLedger.buyerId}.xlsx`);
}

function openReceiptForm() {
    const buyerId = $("#ledgerBuyerSelect").val();
    if (!buyerId) {
        $("#ledgerStatus").text("Select a buyer before recording a receipt.");
        return;
    }
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
        const receipt = await apiFetch(`/buyer-ledger/${buyerId}/receipts`, {
            method: "POST",
            body: {
                received_date: receiptDate,
                amount,
                payment_method: $("#ledgerReceiptMethod").val() || null,
                reference_number: $("#ledgerReceiptReference").val().trim() || null,
                notes: $("#ledgerReceiptNotes").val().trim() || null
            }
        });
        showToast(
            `Receipt recorded. Rs. ${formatNumber(receipt.allocated_amount)} allocated to invoices; Rs. ${formatNumber(receipt.unapplied_amount)} remains as buyer credit.`,
            "success"
        );
        bootstrap.Modal.getOrCreateInstance(
            document.getElementById("ledgerReceiptModal")
        ).hide();
        $("#ledgerReceiptForm")[0].reset();
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
