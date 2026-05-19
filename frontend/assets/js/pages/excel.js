// import { apiFetch } from "../api.js";
// import { API_BASE } from "../config.js";

// let excelFile = null;
// let excelInvoices = [];
// let initialized = false;
// const EVENTS_NS = ".excelImport";

// export function initExcelImport() {
//     const importBtn = document.getElementById("importExcelBtn");
//     const validateBtn = document.getElementById("validateExcelBtn");
//     const submitBtn = document.getElementById("submitInvoicesBtn");
//     const fileInput = document.getElementById("excelFile");
//     importBtn?.addEventListener("click", uploadExcel);
//     validateBtn?.addEventListener("click", validateInvoices);
//     submitBtn?.addEventListener("click", submitInvoices);
//     fileInput?.addEventListener("change", () => {
//         excelFile = fileInput.files?.[0] || null;
//         const fileNameEl = document.getElementById("selectedFileName");
//         if (fileNameEl) {
//             fileNameEl.innerText = excelFile ? excelFile.name : "";
//         }
//         if (excelFile) {
//             excelInvoices = [];
//             resetValidationState();
//             const previewSection = document.getElementById("invoicePreviewSection");
//             if (previewSection) previewSection.style.display = "none";
//             if (validateBtn) validateBtn.disabled = true;
//             if (submitBtn) submitBtn.disabled = true;
//         }
//     });
//     const previewSection = document.getElementById("invoicePreviewSection");
//     if (previewSection) previewSection.style.display = "none";
//     if (validateBtn) validateBtn.disabled = true;
//     if (submitBtn) submitBtn.disabled = true;
// }

// export function destroyExcelImport() {
//     $(document).off(".excel");
// }

// function setButtonLoading(btn, text) {
//     btn.disabled = true;
//     btn.innerHTML = `<i class="bi bi-arrow-repeat spin"></i> ${text}`;
// }

// function resetButton(btn, text, icon = "bi-upload") {
//     btn.disabled = false;
//     btn.innerHTML = `<i class="bi ${icon}"></i> ${text}`;
// }

// function showError(err, fallback = "Something went wrong") {
//     console.error(err);
//     alert(err?.response?.detail || err.message || fallback);
// }

// async function uploadExcel() {
//     if (!excelFile) {
//         alert("Please choose an Excel file first");
//         return;
//     }
//     const btn = document.getElementById("importExcelBtn");
//     const previewSection = document.getElementById("invoicePreviewSection");
//     const validateBtn = document.getElementById("validateExcelBtn");
//     setButtonLoading(btn, "Importing...");
//     try {
//         const formData = new FormData();
//         formData.append("file", excelFile);
//         const data = await apiFetch("/invoices/preview-excel", {
//             method: "POST",
//             body: formData,
//         });
//         if (!data?.invoices || !Array.isArray(data.invoices)) {
//             throw new Error("Invalid preview response");
//         }
//         excelInvoices = data.invoices;
//         resetValidationState();
//         renderPreviewTable();
//         previewSection.style.display = "block";
//         validateBtn.disabled = false;
//     } catch (err) {
//         showError(err, "Excel import failed");
//     } finally {
//         resetButton(btn, "Import Excel");
//     }
// }

// function renderPreviewTable() {
//     const tbody = document.getElementById("invoicePreviewBody");
//     if (!tbody) return;
//     tbody.innerHTML = "";
//     excelInvoices.forEach((inv, index) => {
//         const rowId = `items-${index}`;
//         const tr = document.createElement("tr");
//         tr.innerHTML = `
//             <td>
//                 <button class="btn btn-sm btn-light toggle-btn">▶</button>
//             </td>
//             <td>${inv.excelInvoiceId}</td>
//             <td>${inv.internalInvoiceNo}</td>
//             <td class="validation-status" data-id="${inv.excelInvoiceId}">
//                 🔴 Not validated
//             </td>
//             <td class="submission-status" data-id="${inv.excelInvoiceId}">
//                 —
//             </td>
//             <td>${inv.invoiceType}</td>
//             <td>${inv.invoiceDate}</td>
//             <td>${inv.sellerNTNCNIC}</td>
//             <td>${inv.sellerBusinessName}</td>
//             <td>${inv.sellerProvince}</td>
//             <td>${inv.sellerAddress}</td>
//             <td>${inv.buyerNTNCNIC}</td>
//             <td>${inv.buyerBusinessName}</td>
//             <td>${inv.buyerProvince}</td>
//             <td>${inv.buyerAddress}</td>
//             <td>${inv.buyerRegistrationType}</td>
//             <td>${inv.invoiceRefNo}</td>
//             <td>
//                 <span class="badge bg-info">
//                     ${(inv.items || []).length} items
//                 </span>
//             </td>
//         `;
//         const itemRow = document.createElement("tr");
//         itemRow.style.display = "none";
//         itemRow.innerHTML = `
//             <td colspan="18">
//                 ${renderItemsTable(inv.items || [])}
//             </td>
//         `;
//         tr.querySelector(".toggle-btn").onclick = () => {
//             const isHidden = itemRow.style.display === "none";
//             itemRow.style.display = isHidden ? "table-row" : "none";
//         };
//         tbody.appendChild(tr);
//         tbody.appendChild(itemRow);
//     });
//     const count = document.getElementById("invoiceCount");
//     if (count) count.innerText = excelInvoices.length;
// }

// function renderItemsTable(items) {
//     return `
//         <table class="table table-sm table-bordered">
//             <thead>
//                 <tr>
//                     <th>HS Code</th>
//                     <th>Description</th>
//                     <th>UOM</th>
//                     <th>Qty</th>
//                     <th>Sale Type</th>
//                     <th>Sales Excl ST</th>
//                     <th>Fixed Retail Price</th>
//                     <th>Rate</th>
//                     <th>Sales Tax</th>
//                     <th>STWH</th>
//                     <th>Extra Tax</th>
//                     <th>F.Tax</th>
//                     <th>FED Payable</th>
//                     <th>Discount</th>
//                     <th>SRO Schedule</th>
//                     <th>SRO Item No.</th>
//                     <th>Total</th>
//                 </tr>
//             </thead>
//             <tbody>
//                 ${items.map(i => `
//                     <tr>
//                         <td>${i.hsCode}</td>
//                         <td>${i.productDescription}</td>
//                         <td>${i.uoM}</td>
//                         <td>${i.quantity}</td>
//                         <td>${i.saleType}</td>
//                         <td>${i.valueSalesExcludingST}</td>
//                         <td>${i.fixedNotifiedValueOrRetailPrice}</td>
//                         <td>${i.rate}</td>
//                         <td>${i.salesTaxApplicable}</td>
//                         <td>${i.salesTaxWithheldAtSource}</td>
//                         <td>${i.extraTax}</td>
//                         <td>${i.furtherTax}</td>
//                         <td>${i.fedPayable}</td>
//                         <td>${i.discount}</td>
//                         <td>${i.sroScheduleNo}</td>
//                         <td>${i.sroItemSerialNo}</td>    
//                         <td>${i.totalValues}</td>
//                     </tr>
//                 `).join("")}
//             </tbody>
//         </table>
//     `;
// }

// async function validateInvoices() {
//     if (!excelInvoices.length) {``
//         alert("Import Excel first")//;
//         return;
//     }
//     const btn = document.getElementById("validateExcelBtn");
//     const submitBtn = document.getElementById("submitInvoicesBtn");
//     setButtonLoading(btn, "Validating...");
//     try {
//         const result = await apiFetch("/invoices/validate-excel", {
//             method: "POST",
//             body: excelInvoices,
//         });
//         const results = result?.results || [];
//         updateValidationStatus(results);
//         const hasBlocking = results.some(r => r.status !== "valid");
//         if (submitBtn) submitBtn.disabled = hasBlocking;
//     } catch (err) {
//         showError(err, "Validation failed");
//         resetButton(btn, "Validate", "bi-check-circle");
//         return;
//     }
//     btn.innerHTML = `<i class="bi bi-check-circle"></i> Validated`;
// }

// function updateValidationStatus(results) {
//     results.forEach(res => {
//         const cell = document.querySelector(
//             `.validation-status[data-id="${res.excelInvoiceId}"]`
//         );
//         if (!cell) return;
//         if (res.status === "valid") {
//             cell.innerHTML = "🟢 Valid";
//         } else if (res.status === "pending") {
//             cell.innerHTML = "🟡 Pending";
//         } else {
//             cell.innerHTML = "🔴 Invalid";
//             showValidationErrors(res);
//         }
//         const inv = excelInvoices.find(i => i.excelInvoiceId === res.excelInvoiceId);
//         if (inv) inv.validationStatus = res.status;
//     });
// }

// function showValidationErrors(res) {
//     const invoiceId = res.excelInvoiceId;    
//     const cell = document.querySelector(
//         `.validation-status[data-id="${invoiceId}"]`
//     );
//     if (!cell) return;
//     const row = cell.closest("tr");
//     if (!row) return;
//     const tbody = row.parentNode;
//     let next = row.nextElementSibling;
//     while (next && next.classList.contains("error-row")) {
//         const temp = next.nextElementSibling;
//         next.remove();
//         next = temp;
//     }
//     const validation = res.response?.validationResponse;
//     let errorHTML = "";
//     if (validation) {
//         if (validation.error) {
//             errorHTML += `
//                 <div>
//                     <strong>FBR Error:</strong> ${validation.error}
//                 </div>
//                 <div style="font-size:12px;color:#666;">
//                     Code: ${validation.errorCode || "-"} |
//                     Status: ${validation.status || "-"}
//                 </div>
//             `;
//         }
//         const statuses = validation.invoiceStatuses || [];
//         if (statuses.length > 0) {
//             errorHTML += `<div><strong>Item Errors:</strong></div>`;
//             statuses.forEach(s => {
//                 if (s.status === "Invalid") {
//                     errorHTML += `
//                         <div>Item ${s.itemSNo}: ${s.error}</div>
//                     `;
//                 }
//             });
//         }
//     }
//     if (!errorHTML && res.error) {
//         errorHTML = `<div>${res.error}</div>`;
//     }
//     if (!errorHTML) {
//         errorHTML = `<div>Unknown validation error</div>`;
//     }
//     const errorRow = document.createElement("tr");
//     errorRow.classList.add("error-row");
//     errorRow.innerHTML = `
//         <td colspan="9" style="color:red;padding:10px;">
//             ${errorHTML}
//         </td>
//     `;
//     tbody.insertBefore(errorRow, row.nextSibling);
// }

// function resetValidationState() {
//     document.querySelectorAll(".error-row").forEach(e => e.remove());
//     excelInvoices.forEach(inv => {
//         delete inv.validationStatus;
//         delete inv.submissionStatus;
//     });
//     const submitBtn = document.getElementById("submitInvoicesBtn");
//     if (submitBtn) submitBtn.disabled = true;
// }

// async function submitInvoices() {
//     const btn = document.getElementById("submitInvoicesBtn");
//     if (!excelInvoices.length) {
//         alert("Import Excel first");
//         return;
//     }
//     const validInvoices = excelInvoices.filter(i => i.validationStatus === "valid");
//     if (!validInvoices.length) {
//         alert("No valid invoices to submit");
//         return;
//     }
//     setButtonLoading(btn, "Submitting...");
//     try {
//         const result = await apiFetch("/invoices/submit-excel", {
//             method: "POST",
//             body: validInvoices,
//         });
//         updateSubmissionStatus(result?.results || []);
//     } catch (err) {
//         showError(err, "Submission failed");
//         resetButton(btn, "Submit to FBR");
//         return;
//     }
//     btn.innerText = "Submitted";
// }

// function updateSubmissionStatus(results) {
//     results.forEach(res => {
//         const cell = document.querySelector(
//             `.submission-status[data-id="${res.excelInvoiceId}"]`
//         );
//         if (!cell) return;
//         if (res.status === "success") {
//             cell.innerHTML = `✅ ${res.irn || "Done"}`;
//         } else if (res.status === "pending") {
//             cell.innerHTML = `⏳ Pending`;
//         } else {
//             cell.innerHTML = `❌ Failed`;
//             showSubmissionError(res);
//         }
//     });
// }

// function showSubmissionError(res) {
//     const row = document.querySelector(
//         `.submission-status[data-id="${res.excelInvoiceId}"]`
//     )?.closest("tr");
//     if (!row) return;
//     const errorRow = document.createElement("tr");
//     errorRow.innerHTML = `
//         <td colspan="9" style="color:red;">
//             ${res.error || "Submission failed"}
//         </td>
//     `;
//     row.parentNode.insertBefore(errorRow, row.nextSibling);
// }

// document.getElementById("downloadTemplateBtn")?.addEventListener("click", () => {
//     window.location.href = `${API_BASE}/static/excel/invoice_template.xlsx`;
// });

import { apiFetch } from "../api.js";
import { API_BASE } from "../config.js";

const EVENTS_NS = ".excelImport";

let initialized = false; 
let excelFile = null;
let excelInvoices = [];

export function initExcelImport() {
    if (initialized) {
        destroyExcelImport();
    }

    initialized = true;

    resetPageState();
    bindEvents();
}

export function destroyExcelImport() {
    if (!initialized) {
        return;
    }

    $(document).off(EVENTS_NS);

    initialized = false;
    excelFile = null;
    excelInvoices = [];
}

function bindEvents() {

    $(document)

        .off(`click${EVENTS_NS}`, "#downloadTemplateBtn")
        .on(`click${EVENTS_NS}`, "#downloadTemplateBtn", downloadTemplate)

        .off(`click${EVENTS_NS}`, "#importExcelBtn")
        .on(`click${EVENTS_NS}`, "#importExcelBtn", uploadExcel)

        .off(`click${EVENTS_NS}`, "#validateExcelBtn")
        .on(`click${EVENTS_NS}`, "#validateExcelBtn", validateInvoices)

        .off(`click${EVENTS_NS}`, "#submitInvoicesBtn")
        .on(`click${EVENTS_NS}`, "#submitInvoicesBtn", submitInvoices)

        .off(`change${EVENTS_NS}`, "#excelFile")
        .on(`change${EVENTS_NS}`, "#excelFile", handleFileChange)

        .off(`click${EVENTS_NS}`, ".toggle-btn")
        .on(`click${EVENTS_NS}`, ".toggle-btn", function () {

            const target = $(this).data("target");
            const $row = $(`#${target}`);

            const isHidden = $row.is(":hidden");

            $row.toggle(isHidden);

            $(this).text(isHidden ? "▼" : "▶");
        });
}

function resetPageState() {

    const previewSection = document.getElementById("invoicePreviewSection");

    const validateBtn =
        document.getElementById("validateExcelBtn");

    const submitBtn =
        document.getElementById("submitInvoicesBtn");

    if (previewSection) {
        previewSection.style.display = "none";
    }

    if (validateBtn) {
        validateBtn.disabled = true;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
    }
}

function handleFileChange() {

    const fileInput =
        document.getElementById("excelFile");

    excelFile =
        fileInput?.files?.[0] || null;

    const fileNameEl =
        document.getElementById("selectedFileName");

    if (fileNameEl) {
        fileNameEl.innerText =
            excelFile ? excelFile.name : "";
    }

    if (!excelFile) {
        return;
    }

    excelInvoices = [];

    resetValidationState();

    const previewSection =
        document.getElementById("invoicePreviewSection");

    const validateBtn =
        document.getElementById("validateExcelBtn");

    const submitBtn =
        document.getElementById("submitInvoicesBtn");

    if (previewSection) {
        previewSection.style.display = "none";
    }

    if (validateBtn) {
        validateBtn.disabled = true;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
    }
}

function downloadTemplate() {

    window.location.assign(
        `${API_BASE}/static/excel/invoice_template.xlsx`
    );
}

function setButtonLoading(btn, text) {

    btn.disabled = true;

    btn.innerHTML =
        `<i class="bi bi-arrow-repeat spin"></i> ${text}`;
}

function resetButton(
    btn,
    text,
    icon = "bi-upload"
) {

    btn.disabled = false;

    btn.innerHTML =
        `<i class="bi ${icon}"></i> ${text}`;
}

function showError(
    err,
    fallback = "Something went wrong"
) {

    console.error(err);

    alert(
        err?.response?.detail
        || err.message
        || fallback
    );
}

async function uploadExcel() {

    if (!excelFile) {
        alert("Please choose an Excel file first");
        return;
    }

    const btn =
        document.getElementById("importExcelBtn");

    const previewSection =
        document.getElementById("invoicePreviewSection");

    const validateBtn =
        document.getElementById("validateExcelBtn");

    setButtonLoading(btn, "Importing...");

    try {

        const formData = new FormData();

        formData.append("file", excelFile);

        const data = await apiFetch(
            "/invoices/preview-excel",
            {
                method: "POST",
                body: formData,
            }
        );

        if (
            !data?.invoices
            || !Array.isArray(data.invoices)
        ) {
            throw new Error(
                "Invalid preview response"
            );
        }

        excelInvoices = data.invoices;

        resetValidationState();

        renderPreviewTable();

        if (previewSection) {
            previewSection.style.display = "block";
        }

        if (validateBtn) {
            validateBtn.disabled = false;
        }

    } catch (err) {

        showError(
            err,
            "Excel import failed"
        );

    } finally {

        resetButton(
            btn,
            "Import Excel"
        );
    }
}

function renderPreviewTable() {

    const tbody =
        document.getElementById(
            "invoicePreviewBody"
        );

    if (!tbody) {
        return;
    }

    tbody.innerHTML = "";

    excelInvoices.forEach((inv, index) => {

        const rowId = `items-${index}`;

        const tr =
            document.createElement("tr");

        tr.innerHTML = `
            <td>
                <button
                    class="btn btn-sm btn-light toggle-btn"
                    data-target="${rowId}">
                    ▶
                </button>
            </td>

            <td>${inv.excelInvoiceId}</td>
            <td>${inv.internalInvoiceNo}</td>

            <td
                class="validation-status"
                data-id="${inv.excelInvoiceId}">
                🔴 Not validated
            </td>

            <td
                class="submission-status"
                data-id="${inv.excelInvoiceId}">
                —
            </td>

            <td>${inv.invoiceType}</td>
            <td>${inv.invoiceDate}</td>
            <td>${inv.sellerNTNCNIC}</td>
            <td>${inv.sellerBusinessName}</td>
            <td>${inv.sellerProvince}</td>
            <td>${inv.sellerAddress}</td>
            <td>${inv.buyerNTNCNIC}</td>
            <td>${inv.buyerBusinessName}</td>
            <td>${inv.buyerProvince}</td>
            <td>${inv.buyerAddress}</td>
            <td>${inv.buyerRegistrationType}</td>
            <td>${inv.invoiceRefNo}</td>

            <td>
                <span class="badge bg-info">
                    ${(inv.items || []).length} items
                </span>
            </td>
        `;

        const itemRow =
            document.createElement("tr");

        itemRow.id = rowId;

        itemRow.style.display = "none";

        itemRow.innerHTML = `
            <td colspan="18">
                ${renderItemsTable(inv.items || [])}
            </td>
        `;

        tbody.appendChild(tr);
        tbody.appendChild(itemRow);
    });

    const count =
        document.getElementById("invoiceCount");

    if (count) {
        count.innerText =
            excelInvoices.length;
    }
}

async function validateInvoices() {
    if (!excelInvoices.length) {``
        alert("Import Excel first")//;
        return;
    }
    const btn = document.getElementById("validateExcelBtn");
    const submitBtn = document.getElementById("submitInvoicesBtn");
    setButtonLoading(btn, "Validating...");
    try {
        const result = await apiFetch("/invoices/validate-excel", {
            method: "POST",
            body: excelInvoices,
        });
        const results = result?.results || [];
        updateValidationStatus(results);
        const hasBlocking = results.some(r => r.status !== "valid");
        if (submitBtn) submitBtn.disabled = hasBlocking;
    } catch (err) {
        showError(err, "Validation failed");
        resetButton(btn, "Validate", "bi-check-circle");
        return;
    }
    btn.innerHTML = `<i class="bi bi-check-circle"></i> Validated`;
}

function updateValidationStatus(results) {
    results.forEach(res => {
        const cell = document.querySelector(
            `.validation-status[data-id="${res.excelInvoiceId}"]`
        );
        if (!cell) return;
        if (res.status === "valid") {
            cell.innerHTML = "🟢 Valid";
        } else if (res.status === "pending") {
            cell.innerHTML = "🟡 Pending";
        } else {
            cell.innerHTML = "🔴 Invalid";
            showValidationErrors(res);
        }
        const inv = excelInvoices.find(i => i.excelInvoiceId === res.excelInvoiceId);
        if (inv) inv.validationStatus = res.status;
    });
}

async function submitInvoices() {
    const btn = document.getElementById("submitInvoicesBtn");
    if (!excelInvoices.length) {
        alert("Import Excel first");
        return;
    }
    const validInvoices = excelInvoices.filter(i => i.validationStatus === "valid");
    if (!validInvoices.length) {
        alert("No valid invoices to submit");
        return;
    }
    setButtonLoading(btn, "Submitting...");
    try {
        const result = await apiFetch("/invoices/submit-excel", {
            method: "POST",
            body: validInvoices,
        });
        updateSubmissionStatus(result?.results || []);
    } catch (err) {
        showError(err, "Submission failed");
        resetButton(btn, "Submit to FBR");
        return;
    }
    btn.innerText = "Submitted";
}

function resetValidationState() {
    document.querySelectorAll(".error-row").forEach(e => e.remove());
    excelInvoices.forEach(inv => {
        delete inv.validationStatus;
        delete inv.submissionStatus;
    });
    const submitBtn = document.getElementById("submitInvoicesBtn");
    if (submitBtn) submitBtn.disabled = true;
}

function renderItemsTable(items) {
    return `
        <table class="table table-sm table-bordered">
            <thead>
                <tr>
                    <th>HS Code</th>
                    <th>Description</th>
                    <th>UOM</th>
                    <th>Qty</th>
                    <th>Sale Type</th>
                    <th>Sales Excl ST</th>
                    <th>Fixed Retail Price</th>
                    <th>Rate</th>
                    <th>Sales Tax</th>
                    <th>STWH</th>
                    <th>Extra Tax</th>
                    <th>F.Tax</th>
                    <th>FED Payable</th>
                    <th>Discount</th>
                    <th>SRO Schedule</th>
                    <th>SRO Item No.</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                ${items.map(i => `
                    <tr>
                        <td>${i.hsCode}</td>
                        <td>${i.productDescription}</td>
                        <td>${i.uoM}</td>
                        <td>${i.quantity}</td>
                        <td>${i.saleType}</td>
                        <td>${i.valueSalesExcludingST}</td>
                        <td>${i.fixedNotifiedValueOrRetailPrice}</td>
                        <td>${i.rate}</td>
                        <td>${i.salesTaxApplicable}</td>
                        <td>${i.salesTaxWithheldAtSource}</td>
                        <td>${i.extraTax}</td>
                        <td>${i.furtherTax}</td>
                        <td>${i.fedPayable}</td>
                        <td>${i.discount}</td>
                        <td>${i.sroScheduleNo}</td>
                        <td>${i.sroItemSerialNo}</td>    
                        <td>${i.totalValues}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function showValidationErrors(res) {
    const invoiceId = res.excelInvoiceId;    
    const cell = document.querySelector(
        `.validation-status[data-id="${invoiceId}"]`
    );
    if (!cell) return;
    const row = cell.closest("tr");
    if (!row) return;
    const tbody = row.parentNode;
    let next = row.nextElementSibling;
    while (next && next.classList.contains("error-row")) {
        const temp = next.nextElementSibling;
        next.remove();
        next = temp;
    }
    const validation = res.response?.validationResponse;
    let errorHTML = "";
    if (validation) {
        if (validation.error) {
            errorHTML += `
                <div>
                    <strong>FBR Error:</strong> ${validation.error}
                </div>
                <div style="font-size:12px;color:#666;">
                    Code: ${validation.errorCode || "-"} |
                    Status: ${validation.status || "-"}
                </div>
            `;
        }
        const statuses = validation.invoiceStatuses || [];
        if (statuses.length > 0) {
            errorHTML += `<div><strong>Item Errors:</strong></div>`;
            statuses.forEach(s => {
                if (s.status === "Invalid") {
                    errorHTML += `
                        <div>Item ${s.itemSNo}: ${s.error}</div>
                    `;
                }
            });
        }
    }
    if (!errorHTML && res.error) {
        errorHTML = `<div>${res.error}</div>`;
    }
    if (!errorHTML) {
        errorHTML = `<div>Unknown validation error</div>`;
    }
    const errorRow = document.createElement("tr");
    errorRow.classList.add("error-row");
    errorRow.innerHTML = `
        <td colspan="9" style="color:red;padding:10px;">
            ${errorHTML}
        </td>
    `;
    tbody.insertBefore(errorRow, row.nextSibling);
}