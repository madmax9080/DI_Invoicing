import { ReferenceCache } from "./reference.js";
import { calculateTaxes } from "./tax_strategies.js";  

export let buyerTaxState = {
    isActive: true,
    applyFurtherTax: false,
    furtherTaxRate: 0,
    autoMode: true
};

const numberFormatter = new Intl.NumberFormat("en-PK", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
});

export function formatAmount(value) {
    const num = Number(value);
    return Number.isFinite(num) ? numberFormatter.format(num) : "0";
}

export function resetSelect($el, placeholder = "Select") {
    $el
        .empty()
        .append(`<option value="">${placeholder}</option>`)
        .val("")
        .trigger("change");
}

export function disableSelect($el, placeholder = "Select") {
    resetSelect($el, placeholder);
    $el.prop("disabled", true);
}

export function enableSelect($el) {
    $el.prop("disabled", false);
}

function num(val, fallback = 0) {
    const n = Number(val);
    return Number.isFinite(n) ? n : fallback;
}

export function normalizeItem(raw) {
    return {
        ...raw,
        quantity: num(raw.quantity),
        valueSalesExcludingST: num(raw.valueSalesExcludingST),
        fixedNotifiedValueOrRetailPrice: num(raw.fixedNotifiedValueOrRetailPrice),
        rateValue: num(raw.rateValue),
        furtherTax: num(raw.furtherTax),
        extraTax: raw.extraTax === "" ? "" : num(raw.extraTax),
        fedPayable: num(raw.fedPayable),
        discount: num(raw.discount),
        salesTaxWithheldAtSource: num(raw.salesTaxWithheldAtSource)
    };
}

export function validateItem(item) {
    if (!item.hsCode) return "HS Code is required";
    if (!item.saleTypeId) return "Sale Type is required";
    if (!item.productDescription) return "Product Description is required";
    if (!item.rateId) return "Rate is required";
    if (!item.uomId) return "Unit of Measure is required";
    if (!item.quantity) return "Quantity is required";
    if(!item.valueSalesExcludingST) return "Value is required"
    if (
        item.saleTypeText.toLowerCase().includes("3rd schedule") &&
        item.fixedNotifiedValueOrRetailPrice <= 0
    ) {
        return "Retail price is required for 3rd Schedule goods";
    }
    return null;
}

export function computeItemTotals(item) {
    const calcItem = {
        ...item,
        extraTax: item.extraTax === "" ? 0 : item.extraTax
    };
    const { salesTaxApplicable, totalValues } =
        calculateTaxes(calcItem);
    return {
        ...item,
        salesTaxApplicable,
        totalValues
    };
}

export function getItemInputValues() {
    const selectedRate = $("#rate option:selected");
    const saleTypeText = $("#saleType").select2("data")[0]?.text || "";
    const rateValue = Number(selectedRate.attr("data-rate-value"));
    const optionalFBRField = (val) => val ? parseFloat(val) : "";
    const sroSelect = document.getElementById("sroSchedule");
    const sroItemSelect = document.getElementById("sroItem");
    const sroId = sroSelect?.value || "";
    const sroText =
        sroId && sroSelect.selectedIndex > -1
            ? sroSelect.options[sroSelect.selectedIndex].text
            : "";
    const sroItemId = sroItemSelect?.value || "";
    const sroItemText =
        sroItemId && sroItemSelect.selectedIndex > -1
            ? sroItemSelect.options[sroItemSelect.selectedIndex].text
            : "";
    return {
        hsCode: $("#hsCode").val(),
        productDescription: $("#productDescription").val().trim(),
        uomId: $("#uoM").val() || "",
        uomText: $("#uoM option:selected").text(),
        quantity: parseFloat($("#quantity").val()),
        valueSalesExcludingST: parseFloat($("#valueSalesExcludingST").val()),
        rateId: selectedRate.val(),
        rateValue,
        rateLabel: selectedRate.text(), 
        saleTypeId: $("#saleType").val(),
        saleTypeLabel: ReferenceCache.saleTypes[$("#saleType").val()],
        saleTypeText,
        discount: parseFloat($("#discount").val()),
        salesTaxWithheldAtSource: parseFloat($("#salesTaxWithheldAtSource").val()),
        furtherTax: parseFloat($("#furtherTax").val()),
        extraTax: optionalFBRField($("#extraTax").val()),
        fedPayable: parseFloat($("#fedPayable").val()),
        fixedNotifiedValueOrRetailPrice: parseFloat($("#fixedNotifiedValueOrRetailPrice").val()),
        sroId,
        sroText,
        sroItemId,
        sroItemText
    };
}

export function recalcItemTotals() {
    const rateOption = $("#rate option:selected");
    const rateValue = Number(rateOption.attr("data-rate-value"));
    const rateLabel = rateOption.text();
    const quantity = Number($("#quantity").val()) || 0;
    if (!rateOption.val() || Number.isNaN(rateValue)) {
        $("#salesTaxApplicable").val(0);
        $("#totalValues").val(0);
        return;
    }
    const saleTypeText = $("#saleType").select2("data")[0]?.text?.trim() || "";
    const item = {
        quantity,                            
        rateLabel,                               
        valueSalesExcludingST: Number($("#valueSalesExcludingST").val()) || 0,
        fixedNotifiedValueOrRetailPrice: Number($("#fixedNotifiedValueOrRetailPrice").val()) || 0,
        quantity: Number($("#quantity").val()) || 0,
        rateValue,
        furtherTax: Number($("#furtherTax").val()) || 0,
        extraTax: Number($("#extraTax").val()) || 0,
        fedPayable: Number($("#fedPayable").val()) || 0,
        discount: Number($("#discount").val()) || 0,
        salesTaxWithheldAtSource: Number($("#salesTaxWithheldAtSource").val()) || 0,
        saleTypeText
    };
    const { salesTaxApplicable, totalValues } = calculateTaxes(item);
    $("#salesTaxApplicable").val(salesTaxApplicable);
    $("#totalValues").val(totalValues);
}

export function applyAutoFurtherTax() {
    if (!buyerTaxState.autoMode) return;
    const valueExcl = Number($("#valueSalesExcludingST").val()) || 0;
    let furtherTax = 0;
    if (buyerTaxState.applyFurtherTax && buyerTaxState.furtherTaxRate > 0) {
        furtherTax = (valueExcl * buyerTaxState.furtherTaxRate) / 100;
    }
    $("#furtherTax").val(furtherTax.toFixed(2));
    recalcItemTotals();
}

export function loadItemIntoForm(item, index) {
    editingIndex = index;
    $("#valueSalesExcludingST").val(item.valueSalesExcludingST);
    $("#furtherTax").val(item.furtherTax);
    $("#extraTax").val(item.extraTax);
    $("#fedPayable").val(item.fedPayable);
    $("#discount").val(item.discount);
    $("#salesTaxWithheldAtSource")
        .val(item.salesTaxWithheldAtSource);
    $("#rate").val(item.rateId).trigger("change");
    recalcItemTotals();
    $("#addItemBtn")
        .text("Update Item")
        .removeClass("btn-primary")
        .addClass("btn-success");
}

export function initDynamicBindings() {
    const RECALC_FIELDS = [
        "#valueSalesExcludingST",
        "#furtherTax",
        "#extraTax",
        "#fedPayable",
        "#discount",
        "#salesTaxWithheldAtSource",
        "#fixedNotifiedValueOrRetailPrice",
        "#quantity"
    ];
    RECALC_FIELDS.forEach(selector => {
        $(document)
            .off("input", selector, recalcItemTotals)
            .on("input", selector, recalcItemTotals);
    });
    $(document)
        .off("change", "#rate", recalcItemTotals)
        .on("change", "#rate", recalcItemTotals);
    $(document)
    .off("input.autoFurtherTax", "#valueSalesExcludingST")
    .on("input.autoFurtherTax", "#valueSalesExcludingST", function () {
        if (buyerTaxState.autoMode) {
            applyAutoFurtherTax();
        }
    });
    $(document)
    .off("input.manualFurtherTax", "#furtherTax")
    .on("input.manualFurtherTax", "#furtherTax", function () {
        buyerTaxState.autoMode = false;
    });
}

export function syncInvoiceMeta() {
    $("#metaInvoiceDate").text(
        $("#invoiceDate").val() || "—"
    );

    $("#metaBuyerNTN").text(
        $("#buyerNTNCNIC").val() || "—"
    );

    $("#metaBuyerName").text(
        $("#buyerBusinessName").val() || "—"
    );
    $("#metaBuyerRegistrationType").text(
        $("#buyerRegistrationType").val() || "—"
    );
}

export const FYManager = {
    key: "selectedFY",
    get() {
        return localStorage.getItem(this.key);
    },
    set(fy) {
        if (!fy) return;
        localStorage.setItem(this.key, fy);
    },
    init(selectId = "globalFySelect") {
        const select =
            document.getElementById(selectId);
        if (!select) return;
        const storedFY = this.get();
        if (storedFY) {
            select.value = storedFY;
        } else {
            const defaultFY =
                select.options[0]?.value;
            if (defaultFY) {
                this.set(defaultFY);
                select.value = defaultFY;
            }
        }
    }
};

export function formatCompactPKR(value) {
    const abs = Math.abs(value);
    if (abs >= 1_000_000_000)
        return "Rs." + (value / 1_000_000_000).toFixed(1) + "B";
    if (abs >= 1_000_000)
        return "Rs." + (value / 1_000_000).toFixed(1) + "M";
    if (abs >= 1_000)
        return "Rs." + (value / 1_000).toFixed(1) + "K";
    return "Rs." + value.toLocaleString("en-PK");
}