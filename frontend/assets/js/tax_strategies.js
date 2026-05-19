const n = v => Number(v) || 0;

function baseTotal(item, salesTaxApplicable) {
    return (
        n(item.valueSalesExcludingST)
        + salesTaxApplicable
        + n(item.furtherTax)
        + n(item.extraTax)
        + n(item.fedPayable)
        - n(item.discount)
        - n(item.salesTaxWithheldAtSource)
    );
}

export function parseRate(rateLabel, rateValue) {
    const label = rateLabel.toLowerCase();
    return {
        isPercent: label.includes("%"),
        isPerUnit:
            label.includes("/") ||
            (!label.includes("%") && Number(rateValue) > 0)
    };
}

export function parsePotChlorate(rateLabel = "", rateValue = 0) {
    const label = rateLabel.toLowerCase();
    const percentMatch = label.match(/(\d+)\s*%/);
    const perUnitMatch = 60
    return {
        percentRate: percentMatch ? Number(percentMatch[1]) : (
            label.includes("%") ? rateValue : 0
        ),
        perUnitRate: perUnitMatch
    };
}

function percentOnValue(item) {
    const { isPercent, isPerUnit } =
        parseRate(item.rateLabel, item.rateValue);
    let tax = 0;
    if (isPercent) {
        tax +=
            (n(item.valueSalesExcludingST) * n(item.rateValue)) / 100
    }
    if (isPerUnit && !item.rateLabel.includes("%")) {
        tax += n(item.quantity) * n(item.rateValue);
    }
    return {
        salesTaxApplicable: tax,
        totalValues: baseTotal(item, tax)
    };
}

function percentOnRetail(item) {
    const retail = n(item.fixedNotifiedValueOrRetailPrice);
    if (retail <= 0) {
        return {
            salesTaxApplicable: 0,
            totalValues: baseTotal(item, 0)
        };
    }
    const tax = (retail * n(item.rateValue)) / 100;
    return {
        salesTaxApplicable: tax,
        totalValues: baseTotal(item, tax)
    };
}

function perUnit(item) {
    const tax = n(item.quantity) * n(item.rateValue);
    return {
        salesTaxApplicable: tax,
        totalValues: baseTotal(item, tax)
    };
}

function zeroTax(item) {
    return {
        salesTaxApplicable: 0,
        totalValues: baseTotal(item, 0)
    };
}

const SaleTypeCalculators = {
    "Goods at standard rate (default)": percentOnValue,
    "Goods at Reduced Rate": percentOnValue, 
    "Petroleum Products": percentOnValue, 
    "Gas to CNG stations": percentOnValue, 
    "Mobile Phones": percentOnValue,
    "Processing/Conversion of Goods": percentOnValue,
    "Goods (FED in ST Mode)": percentOnValue,
    "Electric Vehicle": percentOnValue,
    "Electricity Supply to Retailers": percentOnValue,
    "Cotton ginners": percentOnValue,
    "Telecommunication services": percentOnValue,
    "Steel melting and re-rolling": percentOnValue,
    "Ship breaking": percentOnValue,
    "Toll Manufacturing": percentOnValue,
    "Goods as per SRO.297(|)/2023": percentOnValue,
    "3rd Schedule Goods": percentOnRetail,
    "Non-Adjustable Supplies": zeroTax,
    "SIM": perUnit,
    "CNG Sales": perUnit,
    "Cement /Concrete Block": perUnit,
    "Goods at zero-rate": zeroTax,
    "DTRE goods": zeroTax,
    "Exempt goods": zeroTax,
    "Services (FED in ST Mode)": percentOnValue,
    "Services": percentOnValue,
    "Potassium Chlorate": function potassiumChlorate(item) {
        const { percentRate, perUnitRate } = parsePotChlorate(item.rateLabel, item.rateValue);
        const valueTax = (n(item.valueSalesExcludingST) * percentRate) / 100
        const unitTax = n(item.quantity) * perUnitRate
        const tax = valueTax + unitTax;
        return {
            salesTaxApplicable: tax,
            totalValues: baseTotal(item, tax)
        };
    }
};

export function calculateTaxes(item) {
    const key = (item.saleTypeText || "").trim();
    const calculator =
        SaleTypeCalculators[key] || zeroTax;
    return calculator(item);
}