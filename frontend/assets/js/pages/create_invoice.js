import { showToast } from "../toast.js";
import { apiFetch } from "../api.js";
import { loadProvinces, loadDocumentTypes, loadSaleTypes, loadHSCodes } from "../reference.js"
import { resetSelect, disableSelect, enableSelect } from "../utils.js";
import { initDynamicBindings } from "../utils.js";
import { getItemInputValues } from "../utils.js";
import { syncInvoiceMeta } from "../utils.js";
import { computeItemTotals } from "../utils.js";
import { normalizeItem } from "../utils.js";
import { validateItem } from "../utils.js";
import { formatAmount } from "../utils.js";
import { getProvinceTextById } from "../provinces.js";
import { buyerTaxState } from "../utils.js";
import { applyAutoFurtherTax } from "../utils.js";
import { BuyerService } from "../services/buyer_service.js";

let currentItems = [];
let editingIndex = null;
let currentClient = null;
let initialized = false;
const EVENTS_NS = ".createInvoice";

function getClientId() {
    const id = localStorage.getItem("client_id");
    if (!id || id === "null" || id === "undefined") return null;
    return id;
}

async function loadClientDetails(forceReload = false) {
    try {
        if (!currentClient || forceReload) {
            const clientId = getClientId();
            if (!clientId) {
                showToast(
                    "No client selected. Redirecting...",
                    "warning"
                );
                window.location.href = "/clients";
                return null;
            }
            const client = await apiFetch(
                `/clients/${clientId}`
            );
            if (!client) {
                throw new Error("Empty client response");
            }
            currentClient = client;
        }
        $("#clientNameDisplay").text(
            currentClient.name || "—"
        );
        $("#sellerNTNCNIC").val(
            currentClient.sellerNTNCNIC
        );
        $("#sellerBusinessName").val(
            currentClient.sellerBusinessName
        );
        $("#sellerProvince").val(
            getProvinceTextById(
                currentClient.sellerProvince
            )
        );
        $("#sellerAddress").val(
            currentClient.sellerAddress
        );
        $("#sellerNTNCNIC, #sellerBusinessName, #sellerProvince, #sellerAddress")
            .prop("readonly", true)
            .addClass("bg-light text-muted");
        return currentClient;
    } catch (err) {
        showToast(
            "Client not found. Please reselect.",
            "error"
        );
        localStorage.removeItem("client_id");
        localStorage.removeItem("client_name");
        currentClient = null;
        setTimeout(() => {
            window.location.href = "/clients";
        }, 1200);
        return null;
    }
}

async function loadReferences() {
    const client = currentClient || await loadClientDetails();
    if (!client) {
        console.warn("Skipping references: no client");
        return;
    }
    await Promise.all([
        loadProvinces($("#buyerProvince")),
        loadDocumentTypes($("#invoiceType")),
        loadSaleTypes($("#saleType")),
        loadHSCodes($("#hsCode")),
    ]);
}

// use to find if the buyer is active or not and if further tax is applicable or not and the rate of further tax if applicable
async function handleBuyerValidation() {
    const ntn = $(this).val().trim();
    if (!ntn) return;
    const result = await validateBuyer(ntn);
    if (!result) return;
    buyerTaxState.isActive = result.is_active;
    buyerTaxState.applyFurtherTax = result.apply_further_tax;
    buyerTaxState.furtherTaxRate = result.further_tax_rate;
    buyerTaxState.autoMode = true;
    applyAutoFurtherTax();
};
//Allowed UOMs i.e KG
let uomRequestId = 0;
async function handleHSCodeChange() {
    const hsCode = $(this).val();
    const $uom = $("#uoM");
    disableSelect($uom, "Select UOM");
    if (!hsCode) return;
    const reqId = ++uomRequestId;
    try {
        const uoms = await apiFetch(
            `/dynamic/hs_uoms?hs_code=${encodeURIComponent(hsCode)}&annexure_id=3`
        );
        if (reqId !== uomRequestId) return;
        uoms.forEach(u => {
            $uom.append(
                new Option(u.description, u.uoM_ID, false, false)
            );
        });
        enableSelect($uom);
    } catch (err) {
        // console.error("UOM load failed:", err);
        resetSelect($uom, "Failed to load UOMs");
    }
};
//Sales Type i.e. goods at standard rate
let rateRequestId = 0;
async function handleSaleTypeChange() {
    const transTypeId = $(this).val();
    const $rate = $("#rate");
    disableSelect($rate, "Select Rate");
    disableSelect($("#sroSchedule"), "Select SRO");
    disableSelect($("#sroItem"), "Select SRO Item");
    if (!transTypeId) return;
    const invoiceDate =
        $("#invoiceDate").val() || new Date().toISOString().slice(0, 10);
    const reqId = ++rateRequestId;
    try {
        const sellerProvinceId = (currentClient && currentClient.sellerProvince) ? currentClient.sellerProvince : ( $("#sellerProvince").val() || "" );
        const rates = await apiFetch(
            `/dynamic/sale_type_rates?date=${invoiceDate}&trans_type_id=${transTypeId}${sellerProvinceId ? `&origination_supplier=${encodeURIComponent(sellerProvinceId)}` : ""}`
        );
        if (reqId !== rateRequestId) return;
        rates.forEach(r => {
            const rateValue = Number(r.ratE_VALUE) || 0;
            const label = r.ratE_DESC || `${rateValue}%`;
            const opt = new Option(label, r.ratE_ID, false, false);
            opt.dataset.rateValue = rateValue;
            $rate.append(opt);
        });
        enableSelect($rate);
    } catch (err) {
        resetSelect($rate, "Failed to load rates");
    }
};
//SRO Schedule i.e. 1125(1)
let sroRequestId = 0;
async function handleRateChange() {
    const rateId = $(this).val();
    const $sro = $("#sroSchedule");
    disableSelect($sro, "Select SRO");
    disableSelect($("#sroItem"), "Select SRO Item");
    if (!rateId) return;
    const invoiceDate =
        $("#invoiceDate").val() || new Date().toISOString().slice(0, 10);
    const reqId = ++sroRequestId;
    try {
        const sellerProvinceId = (currentClient && currentClient.sellerProvince) ? currentClient.sellerProvince : ( $("#sellerProvince").val() || "" );
        const sros = await apiFetch(
            `/dynamic/sro_schedules?rate_id=${rateId}&date=${invoiceDate}&origination_supplier_csv=${sellerProvinceId}`
        );
        if (reqId !== sroRequestId) return;
        if (!sros.length) {
            resetSelect($sro, "No SRO Found");
            return;
        }
        sros.forEach(s => {
            if (s.srO_ID) {
                $sro.append(
                    new Option(s.srO_DESC, s.srO_ID, false, false)
                );
            }
        });
        enableSelect($sro);
    } catch (err) {
        resetSelect($sro, "Failed to load SRO");
    }
};
// SRO Item i.e. 1
let sroItemRequestId = 0;
async function handleSROScheduleChange() {
    const sroId = $(this).val();
    const $sroItem = $("#sroItem");
    disableSelect($sroItem, "Select SRO Item");
    if (!sroId) return;
    const invoiceDate =
        $("#invoiceDate").val() || new Date().toISOString().slice(0, 10);
    const reqId = ++sroItemRequestId;
    try {
        const items = await apiFetch(
            `/dynamic/sro_items?date=${invoiceDate}&sro_id=${sroId}`
        );
        if (reqId !== sroItemRequestId) return;
        if (!items.length) {
            resetSelect($sroItem, "No SRO Items");
            return;
        }
        items.forEach(item => {
            if (item.srO_ITEM_ID) {
                $sroItem.append(
                    new Option(item.srO_ITEM_DESC, item.srO_ITEM_ID, false, false)
                );
            }
        });
        enableSelect($sroItem);
    } catch (err) {
        resetSelect($sroItem, "Failed to load SRO Items");
    }
};
// Add item to table
async function handleAddItem() {
    const raw = getItemInputValues();
    const normalized = normalizeItem(raw);
    const error = validateItem(normalized);
    if (error) {
        showToast(error, "warning");
        return;
    }
    const finalItem = computeItemTotals(normalized);
    if (editingIndex !== null) {
        currentItems[editingIndex] = finalItem;
        editingIndex = null;
        $("#addItemBtn")
            .text("Add Item")
            .removeClass("btn-success")
            .addClass("btn-primary");
    } else {
        currentItems.push(finalItem);
        console.log(currentItems);
    }
    renderItemsTable();
    clearItemInputs();
};

async function validateBuyer(registrationNo) {
    try {
        return await apiFetch("/dynamic/validate_buyer", {
            method: "POST",
            body: {
                registration_no: registrationNo
            }
        });
    } catch (err) {
        return null;
    }
}

function renderItemsTable() {
    const tbody = $("#itemsTable");
    tbody.empty();
    let subtotal = 0;
    let taxTotal = 0;
    let grandTotal = 0;
    currentItems.forEach((item, index) => {
        const valueExcl = Number(item.valueSalesExcludingST) || 0;
        const salesTax = Number(item.salesTaxApplicable) || 0;
        const totalVal = Number(item.totalValues) || 0;
        subtotal += valueExcl;
        taxTotal += salesTax;
        grandTotal += totalVal;
        tbody.append(buildItemRow(item, index));
    });
    $("#subtotalCell").text(formatAmount(subtotal));
    $("#taxTotalCell").text(formatAmount(taxTotal));
    $("#grandTotalCell").text(formatAmount(grandTotal));
}

function buildItemRow(item, index) {
    return `
        <tr data-index="${index}">
            <td>${index + 1}</td>
            <td class="text-center">
                <div class="action-buttons">
                    <button
                        type="button"
                        class="btn btn-outline-primary btn-sm edit-item"
                        title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button
                        type="button"
                        class="btn btn-outline-danger btn-sm remove-item"
                        title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
            <td class="fw-semibold">${escapeHtml(item.hsCode)}</td>
            <td class="fw-medium">${escapeHtml(item.productDescription)}</td>
            <td>${escapeHtml(item.saleTypeLabel)}</td>
            <td class="text-end">${formatQty(item.quantity)}</td>
            <td>${escapeHtml(item.uomText)}</td>
            <td class="text-end">
                ${formatRate(item.rateLabel, item.rateValue)}
            </td>
            <td class="text-end">${formatAmount(item.valueSalesExcludingST)}</td>
            <td class="text-end">${formatAmount(item.fixedNotifiedValueOrRetailPrice)}</td>
            <td class="text-end">${formatAmount(item.salesTaxApplicable)}</td>
            <td class="text-end">${formatAmount(item.furtherTax)}</td>
            <td class="text-end">${formatAmount(item.fedPayable)}</td>
            <td class="text-end">${formatAmount(item.salesTaxWithheldAtSource)}</td>
            <td class="text-end">${formatOptional(item.extraTax)}</td>
            <td class="text-end">${formatAmount(item.discount)}</td>
            <td class="text-end fw-semibold">${formatAmount(item.totalValues)}</td>
            <td><small>${escapeHtml(item.sroText || "-")}</small></td>
            <td><small>${escapeHtml(item.sroItemText || "-")}</small></td>
        </tr>
    `;
}

function formatQty(val) {
    const n = Number(val);
    return Number.isFinite(n) ? n.toFixed(2) : "0.00";
}

function formatOptional(val) {
    const n = Number(val);
    return n > 0 ? n.toFixed(2) : "-";
}

function formatRate(rateLabel, rateValue) {
    if (!rateLabel) return "-";
    if (/[/%]|rs|per|\/|kg|mt|bill|sqm/i.test(rateLabel)) {
        return escapeHtml(rateLabel);
    }
    return Number.isFinite(rateValue)
        ? rateValue.toString()
        : escapeHtml(rateLabel);
}

function escapeHtml(text) {
    return String(text ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function clearItemInputs() {
    const TEXT_FIELDS = [
        "#productDescription",
        "#quantity",
        "#valueSalesExcludingST",
        "#salesTaxApplicable",
        "#totalValues",
        "#discount",
        "#salesTaxWithheldAtSource",
        "#furtherTax",
        "#extraTax",
        "#fedPayable",
        "#fixedNotifiedValueOrRetailPrice"
    ];
    const SELECT_FIELDS = [
        "#hsCode",
        "#uoM",
        "#saleType",
        "#rate",
        "#sroSchedule",
        "#sroItem"
    ];
    TEXT_FIELDS.forEach(sel => {
        $(sel).val("");
    });
    SELECT_FIELDS.forEach(sel => {
        $(sel).val("").trigger("change");
    });
    editingIndex = null;
    $("#addItemBtn")
        .text("Add Item")
        .removeClass("btn-success")
        .addClass("btn-primary");
    $("#cancelEditBtn").addClass("d-none");
}

async function editItem(index) {
    const item = currentItems[index];
    editingIndex = index;   
    $("#productDescription").val(item.productDescription);
    $("#quantity").val(item.quantity);
    $("#valueSalesExcludingST").val(item.valueSalesExcludingST);
    $("#discount").val(item.discount);
    $("#salesTaxWithheldAtSource").val(item.salesTaxWithheldAtSource);
    $("#furtherTax").val(item.furtherTax);
    $("#extraTax").val(item.extraTax);
    $("#fedPayable").val(item.fedPayable);
    $("#fixedNotifiedValueOrRetailPrice").val(item.fixedNotifiedValueOrRetailPrice);
    $("#salesTaxApplicable").val(Number(item.salesTaxApplicable).toFixed(2));
    $("#totalValues").val(Number(item.totalValues).toFixed(2));
    $("#addItemBtn")
        .text("Update Item")
        .removeClass("btn-primary")
        .addClass("btn-success");
    $("#cancelEditBtn").removeClass("d-none");  
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function removeItem(index) {
    if (index === undefined || index === null) return;
    if (!currentItems[index]) return;
    currentItems.splice(index, 1);
    if (editingIndex === index) {
        editingIndex = null;
        $("#addItemBtn")
            .text("Add Item")
            .removeClass("btn-success")
            .addClass("btn-primary");
        clearItemInputs();
    }
    if (editingIndex !== null && index < editingIndex) {
        editingIndex--;
    }
    renderItemsTable();
}

function bindItemTableHandlers() {
    const $table = $("#itemsTable");
    $table.off(EVENTS_NS);
    $table.on(`click${EVENTS_NS}`, ".edit-item", function () {
        const index = $(this)
            .closest("tr")
            .data("index");
        if (index !== undefined) {
            editItem(index);
        }
    });
    $table.on(`click${EVENTS_NS}`, ".remove-item", function () {
        const index = $(this)
            .closest("tr")
            .data("index");
        if (index !== undefined) {
            removeItem(index);
        }
    });
}

async function loadBuyerByNTN(ntn) {
    try {
        if (!ntn?.trim()) {
            return;
        }
        const buyer =
            await BuyerService.getBuyerByNTN(
                ntn.trim()
            );
        if (!buyer) {
            return;
        }
        $("#buyerBusinessName").val(
            buyer.name || ""
        );
        const provinceOption =
        $("#buyerProvince option")
            .filter(function () {
                return (
                    $(this).text().trim().toLowerCase()
                    ===
                    String(buyer.province || "")
                        .trim()
                        .toLowerCase()
                );
            })
            .first();
        if (provinceOption.length) {
            $("#buyerProvince")
                .val(provinceOption.val())
                .trigger("change");
        }
        $("#buyerAddress").val(
            buyer.address || ""
        );
        $("#buyerRegistrationType").val(
            buyer.buyer_registration_type || ""
        );
    } catch (error) {
        if (error.status !== 404) {
            console.error(
                "Buyer lookup failed:",
                error
            );
        }
    }
}

async function handleSubmitInvoice() {
    const $btn = $(this);
    if ($btn.prop("disabled")) return;
    const n = v => {
        const num = Number(v);
        return Number.isFinite(num) ? Number(num.toFixed(2)) : 0;
    };
    $btn.prop("disabled", true).text("Submitting...");
    try {
        if (!currentItems.length) {
            const err = new Error("Please add at least one item");
            err.isValidation = true;
            throw err;
        }
        const invoiceDate = $("#invoiceDate").val();
        if (!invoiceDate) {
            const err = new Error("Invoice Date is required");
            err.isValidation = true;
            throw err;
        }
        const buyerBusinessName =
            $("#buyerBusinessName").val().trim();
        if (!buyerBusinessName) {
            const err = new Error("Buyer Business Name is required");
            err.isValidation = true;
            throw err;
        }
        const client =
            currentClient || await loadClientDetails();
        if (!client) {
            const err = new Error("Client details not available");
            err.isValidation = true;
            throw err;
        }
        const internalInvoiceNo = $("#internalInvoiceNo").val().trim();
        if (!internalInvoiceNo) {
            const err = new Error("Invoice Number is required");
            err.isValidation = true;
            throw err;
        }
        const payload = {
            internalInvoiceNo,
            invoiceType: $("#invoiceType option:selected").text(),
            invoiceDate,
            invoiceRefNo: $("#invoiceRefNo").val() || "",
            // scenarioId: $("#scenarioId").val() || "",
            sellerNTNCNIC: client.sellerNTNCNIC,
            sellerBusinessName: client.sellerBusinessName,
            sellerProvince: getProvinceTextById(client.sellerProvince),
            sellerAddress: client.sellerAddress,
            buyerNTNCNIC: $("#buyerNTNCNIC").val(),
            buyerBusinessName,
            buyerProvince: $("#buyerProvince option:selected").text(),
            buyerAddress: $("#buyerAddress").val(),
            buyerRegistrationType: $("#buyerRegistrationType").val(),
            items: currentItems.map(item => ({
                hsCode: item.hsCode,
                productDescription: item.productDescription,
                rate: item.rateLabel,
                uoM: item.uomText,
                quantity: n(item.quantity),
                valueSalesExcludingST: n(item.valueSalesExcludingST),
                salesTaxApplicable: n(item.salesTaxApplicable),
                totalValues: n(item.totalValues),
                fixedNotifiedValueOrRetailPrice: n(
                    item.fixedNotifiedValueOrRetailPrice
                ),
                salesTaxWithheldAtSource: n(
                    item.salesTaxWithheldAtSource
                ),
                furtherTax: n(item.furtherTax),
                extraTax: normalizeExtraTax(
                    item.extraTax,
                    item.saleTypeLabel
                ),
                fedPayable: n(item.fedPayable),
                discount: n(item.discount),
                saleType: item.saleTypeLabel,
                sroScheduleNo: item.sroText || "",
                sroItemSerialNo: item.sroItemText || ""
            }))
        };
        // console.log("Submitting to FBR:", payload);
        const response = await apiFetch("/invoices/post", {
            method: "POST",
            body: payload
        });
        // console.log("Backend Response:", response);
        if (response?.status === "success") {
            showToast(
                `Invoice Posted. FBR No: ${response.fbrInvoiceNumber}`,
                "success",
                "Success"
            );
            $("#internalInvoiceNo").val("");
            currentItems = [];
            renderItemsTable();
            return;
        }
        if (response?.status === "invalid") {
            const fbr = response?.fbr_response;
            const validation = fbr?.validationResponse;
            const statuses = validation?.invoiceStatuses || [];
            if (!statuses.length) {
                showToast(
                    `${validation.error}`,
                    "error",
                    `Error Code ${validation.errorCode}`
                );
                return;
            }
            statuses.forEach(item => {
                if (item.status === "Invalid") {
                    showToast(
                        `Item ${item.itemSNo}: ${item.error}`,
                        "error",
                        `Error Code ${item.errorCode}`
                    );
                }
            });
            return;
        }
        if (response?.status === "already_posted") {
            showToast(
                `Invoice No. ${internalInvoiceNo} already posted with FBR No: ${response.fbrInvoiceNumber}`,
                "warning",
                "Duplicate"
            );
            return;
        }
    } catch (err) {
        if (err.isValidation) {
            showToast(err.message, "warning");
        }
        // console.error("Invoice submission error:", err);
    } finally {
        $btn.prop("disabled", false)
            .text("Submit Invoice to FBR");
    }
};

const SALE_TYPES_WITH_EMPTY_EXTRA_TAX = new Set([
    "Goods at Reduced Rate", "Exempt goods"
]);

function normalizeExtraTax(extraTax, saleTypeLabel) {
    if (SALE_TYPES_WITH_EMPTY_EXTRA_TAX.has(saleTypeLabel)) {
        return "";
    }
    if (extraTax === "" || extraTax === null || extraTax === undefined) {
        return 0;
    }
    return Number(extraTax);
}

export async function initCreateInvoice() {
    if (initialized) {
        destroyCreateInvoice();
    }
    initialized = true;
    const client = await loadClientDetails();
    if (!client) {
        return;
    }
    await loadReferences();
    initDynamicBindings();
    bindItemTableHandlers();
    bindStaticEvents();
    syncInvoiceMeta();
    $("#invoiceDate, #buyerNTNCNIC, #buyerBusinessName, #buyerRegistrationType")
        .off(EVENTS_NS)
        .on(
            `change${EVENTS_NS} keyup${EVENTS_NS}`,
            syncInvoiceMeta
        );
    initSelect2();
    $("#salesTaxApplicable")
        .prop("readonly", true)
        .addClass("bg-light text-muted");
    renderItemsTable();
}

function bindStaticEvents() {
    $(document)
    .off(`blur${EVENTS_NS}`, "#buyerNTNCNIC")
    .on(    
        `blur${EVENTS_NS}`,
        "#buyerNTNCNIC",
        async function () {
            const ntn = $(this)
                .val()
                .trim();
            if (!ntn) {
                return;
            }
            await loadBuyerByNTN(ntn);
            await handleBuyerValidation.call(this);
        }
    );
    $("#hsCode")
        .off(`change${EVENTS_NS}`)
        .on(`change${EVENTS_NS}`, handleHSCodeChange);
    $("#saleType")
        .off(`change${EVENTS_NS}`)
        .on(`change${EVENTS_NS}`, handleSaleTypeChange);
    $("#rate")
        .off(`change${EVENTS_NS}`)
        .on(`change${EVENTS_NS}`, handleRateChange);
    $("#sroSchedule")
        .off(`change${EVENTS_NS}`)
        .on(`change${EVENTS_NS}`, handleSROScheduleChange);
    $("#addItemBtn")
        .off(`click${EVENTS_NS}`)
        .on(`click${EVENTS_NS}`, handleAddItem);
    $("#submitInvoiceBtn")
        .off(`click${EVENTS_NS}`)
        .on(`click${EVENTS_NS}`, handleSubmitInvoice);
    $("#cancelEditBtn")
        .off(`click${EVENTS_NS}`)
        .on(`click${EVENTS_NS}`, () => {
            editingIndex = null;
            clearItemInputs();
        });
}

function initSelect2() {
    const selectors = [
        "#rate",
        "#uoM",
        "#sroSchedule",
        "#sroItem"
    ];
    selectors.forEach(selector => {
        const $el = $(selector);
        if ($el.hasClass("select2-hidden-accessible")) {
            $el.select2("destroy");
        }
        $el.select2({
            placeholder: "Select option",
            allowClear: true,
            width: "100%"
        });
    });
}

export function destroyCreateInvoice() {
    $(document).off(EVENTS_NS);
    $("#itemsTable").off(EVENTS_NS);
    [
        "#buyerNTNCNIC",
        "#hsCode",
        "#saleType",
        "#rate",
        "#sroSchedule",
        "#addItemBtn",
        "#submitInvoiceBtn",
        "#cancelEditBtn",
        "#invoiceDate",
        "#buyerBusinessName",
        "#buyerRegistrationType"
    ].forEach(selector => {
        $(selector).off(EVENTS_NS);
    });
    [
        "#rate",
        "#uoM",
        "#sroSchedule",
        "#sroItem"
    ].forEach(selector => {
        const $el = $(selector);
        if ($el.hasClass("select2-hidden-accessible")) {
            $el.select2("destroy");
        }
    });
    initialized = false;
}