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
        itemRate: num(raw.itemRate),
        valueSalesExcludingST: num(raw.valueSalesExcludingST),
        fixedNotifiedValueOrRetailPrice: num(raw.fixedNotifiedValueOrRetailPrice),
        rateValue: num(raw.rateValue),
        furtherTax: num(raw.furtherTax),
        extraTax: raw.extraTax === "" ? "" : num(raw.extraTax),
        fedPayable: num(raw.fedPayable),
        tax236HRate: num(raw.tax236HRate),
        tax236H: num(raw.tax236H),
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
    if (!item.quantity || item.quantity <= 0) {
        return "Quantity is required";
    }
    if (!item.valueSalesExcludingST || item.valueSalesExcludingST <= 0) {
        return "Value is required";
    }
    if (
        item.itemRate === undefined ||
        item.itemRate === null ||
        !Number.isFinite(Number(item.itemRate))
    ) {
        return "Rate is required";
    }
    if (
        item.saleTypeText.toLowerCase().includes("3rd schedule") &&
        item.fixedNotifiedValueOrRetailPrice <= 0
    ) {
        return "Retail price is required for 3rd Schedule goods";
    }
    return null;
}

// export function computeItemTotals(item) {
//     const calcItem = {
//         ...item,
//         extraTax: item.extraTax === "" ? 0 : item.extraTax
//     };
//     const { salesTaxApplicable, totalValues } = calculateTaxes(calcItem);
//     return {
//         ...item,
//         salesTaxApplicable,
//         totalValues
//     };
// }

export function computeItemTotals(item) {
    const calcItem = {
        ...item,
        extraTax: item.extraTax === "" ? 0 : item.extraTax
    };
    const {
        salesTaxApplicable,
        totalValues
    } = calculateTaxes(calcItem);
    // Calculate 236H (on invoice value before discount)
    const tax236H =
        (
            (
                Number(calcItem.valueSalesExcludingST) || 0
            ) +
            salesTaxApplicable +
            (Number(calcItem.furtherTax) || 0) +
            (Number(calcItem.extraTax) || 0) +
            (Number(calcItem.fedPayable) || 0)
        ) *
        ((Number(calcItem.tax236HRate) || 0) / 100);
    const grandTotal = totalValues + tax236H;
    $("#salesTaxApplicable").val(salesTaxApplicable.toFixed(2));
    $("#tax236H").val(tax236H.toFixed(2));
    $("#totalValues").val(grandTotal.toFixed(2));
    return {
        ...item,
        salesTaxApplicable,
        tax236H,
        totalValues: grandTotal
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
        itemRate: parseFloat($("#itemRate").val()),
        saleTypeId: $("#saleType").val(),
        saleTypeLabel: ReferenceCache.saleTypes[$("#saleType").val()],
        saleTypeText,
        discount: parseFloat($("#discount").val()),
        salesTaxWithheldAtSource: parseFloat($("#salesTaxWithheldAtSource").val()),
        furtherTax: parseFloat($("#furtherTax").val()),
        extraTax: optionalFBRField($("#extraTax").val()),
        fedPayable: parseFloat($("#fedPayable").val()),
        tax236HRate: Number($("#tax236HRate").val()) || 0,
        tax236H: Number($("#tax236H").val()) || 0,
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
        $("#tax236H").val("0.00");
        $("#totalValues").val(0);
        return;
    }
    const saleTypeText = $("#saleType").select2("data")[0]?.text?.trim() || "";
    const item = {
        quantity,                            
        rateLabel,                               
        valueSalesExcludingST: Number($("#valueSalesExcludingST").val()) || 0,
        fixedNotifiedValueOrRetailPrice: Number($("#fixedNotifiedValueOrRetailPrice").val()) || 0,
        // quantity: Number($("#quantity").val()) || 0,
        rateValue,
        furtherTax: Number($("#furtherTax").val()) || 0,
        extraTax: Number($("#extraTax").val()) || 0,
        fedPayable: Number($("#fedPayable").val()) || 0,
        discount: Number($("#discount").val()) || 0,
        salesTaxWithheldAtSource: Number($("#salesTaxWithheldAtSource").val()) || 0,
        saleTypeText,
        tax236HRate: Number($("#tax236HRate").val()) || 0,
        tax236H: Number($("#tax236H").val()) || 0,
    };
    computeItemTotals(item);
}

export function syncItemRateAndValue(source) {
    const quantityRaw = $("#quantity").val().trim();
    const rateRaw = $("#itemRate").val().trim();
    const valueRaw = $("#valueSalesExcludingST").val().trim();
    const quantity = Number(quantityRaw);
    const rate = Number(rateRaw);
    const value = Number(valueRaw);
    // ---------------------------------------------------------
    // USER ENTERED ITEM RATE
    // Quantity × Item Rate = Amount
    // ---------------------------------------------------------
    if (source === "rate") {
        if (
            quantityRaw !== "" &&
            quantity > 0 &&
            rateRaw !== "" &&
            Number.isFinite(rate)
        ) {
            $("#valueSalesExcludingST").val(
                (quantity * rate).toFixed(2)
            );
        }
        applyAutoFurtherTax();
        return;
    }
    // ---------------------------------------------------------
    // USER ENTERED QUANTITY
    //
    // If item rate exists:
    //      Quantity × Rate = Amount
    //
    // If item rate does NOT exist but amount exists:
    //      Amount ÷ Quantity = Rate
    // ---------------------------------------------------------
    if (source === "quantity") {
        if (
            quantityRaw !== "" &&
            quantity > 0 &&
            rateRaw !== "" &&
            Number.isFinite(rate)
        ) {
            // Rate exists → calculate amount
            $("#valueSalesExcludingST").val(
                (quantity * rate).toFixed(2)
            );
        }
        else if (
            quantityRaw !== "" &&
            quantity > 0 &&
            rateRaw === "" &&
            valueRaw !== "" &&
            Number.isFinite(value)
        ) {
            // Amount exists but rate does not
            // → calculate rate from amount
            $("#itemRate").val(
                (value / quantity).toFixed(2)
            );
        }
        applyAutoFurtherTax();
        return;
    }
    // ---------------------------------------------------------
    // USER ENTERED AMOUNT
    //
    // If quantity exists:
    //      Amount ÷ Quantity = Rate
    //
    // If quantity does not exist:
    //      Keep rate empty.
    //      Amount remains the source value.
    // ---------------------------------------------------------
    if (source === "value") {
        if (
            quantityRaw !== "" &&
            quantity > 0 &&
            valueRaw !== "" &&
            Number.isFinite(value)
        ) {
            // Quantity exists → calculate rate
            $("#itemRate").val(
                (value / quantity).toFixed(2)
            );
        }
        else if (
            quantityRaw === ""
        ) {
            // Amount was entered first.
            // Do NOT allow the amount to become the item rate.
            $("#itemRate").val("");
        }
        applyAutoFurtherTax();
        return;
    }
    recalcItemTotals();
}

// export function applyAutoFurtherTax() {
//     if (!buyerTaxState.autoMode) return;
//     const valueExcl = Number($("#valueSalesExcludingST").val()) || 0;
//     let furtherTax = 0;
//     if (buyerTaxState.applyFurtherTax && buyerTaxState.furtherTaxRate > 0) {
//         furtherTax = (valueExcl * buyerTaxState.furtherTaxRate) / 100;
//     }
//     $("#furtherTax").val(furtherTax.toFixed(2));
//     recalcItemTotals();
// }

export function applyAutoFurtherTax() {
    if (!buyerTaxState.autoMode) {
        recalcItemTotals();
        return;
    }
    const valueExcl =
        Number($("#valueSalesExcludingST").val()) || 0;
    let furtherTax = 0;
    if (
        buyerTaxState.applyFurtherTax &&
        buyerTaxState.furtherTaxRate > 0
    ) {
        furtherTax =
            (valueExcl * buyerTaxState.furtherTaxRate) / 100;
    }
    $("#furtherTax").val(
        furtherTax.toFixed(2)
    );
    recalcItemTotals();
}

export function loadItemIntoForm(item, index) {
    editingIndex = index;
    $("#itemRate").val(item.itemRate);
    $("#quantity").val(item.quantity);
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
        "#furtherTax",
        "#extraTax",
        "#fedPayable",
        "#discount",
        "#salesTaxWithheldAtSource",
        "#fixedNotifiedValueOrRetailPrice",
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
    .off("input.itemRate", "#itemRate")
    .on("input.itemRate", "#itemRate", function () {
        syncItemRateAndValue("rate");
    });
    $(document)
        .off("input.itemQuantity", "#quantity")
        .on("input.itemQuantity", "#quantity", function () {
            syncItemRateAndValue("quantity");
        });
    $(document)
        .off("input.itemValue", "#valueSalesExcludingST")
        .on("input.itemValue", "#valueSalesExcludingST", function () {
            syncItemRateAndValue("value");
        });
     $(document)
        .off("change", "#tax236HRate", recalcItemTotals)
        .on("change", "#tax236HRate", recalcItemTotals);
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