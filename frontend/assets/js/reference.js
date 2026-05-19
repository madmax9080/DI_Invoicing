import { apiFetch } from "./api.js";
import { resetSelect } from "./utils.js";

const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours
function getCached(key) {
    const raw = localStorage.getItem(`ref_${key}`);
    if (!raw) return null;
    try {
        const parsed = JSON.parse(raw);
        if (Date.now() - parsed.timestamp < CACHE_TTL) {
            return parsed.data;
        }
    } catch {}
    return null;
}

function setCached(key, data) {
    localStorage.setItem(
        `ref_${key}`,
        JSON.stringify({
            data,
            timestamp: Date.now()
        })
    );
}

export const ReferenceCache = {
    provinces: {},
    docTypes: {},
    saleTypes: {},
    hsCodes: {},
};

function initSelect2($el, data, placeholder) {
    resetSelect($el);
    $el.append(new Option("", "", true, false));
    data.forEach(d => {
        $el.append(new Option(d.text, d.id, false, false));
    });
    $el.select2({
        placeholder,
        allowClear: true,
        width: "100%",
    });
    $el.val(null).trigger("change");
}

export async function loadProvinces($select) {
    let provinces = getCached("provinces");
    if (!provinces) {
        provinces = await apiFetch("/reference/provinces");
        setCached("provinces", provinces);
    }
    const data = provinces.map(p => {
        ReferenceCache.provinces[p.stateProvinceCode] = p.stateProvinceDesc;
        return {
            id: p.stateProvinceCode,
            text: p.stateProvinceDesc,
        };
    });
    initSelect2($select, data, "Select Province");
}

export async function loadDocumentTypes($select) {
    let types = getCached("document_types");
    if (!types) {
        types = await apiFetch("/reference/document_types");
        setCached("document_types", types);
    }
    const data = types.map(d => {
        ReferenceCache.docTypes[d.docTypeId] = d.docDescription;
        return {
            id: d.docTypeId,
            text: d.docDescription,
        };
    });
    initSelect2($select, data, "Select Invoice Type");
}

export async function loadSaleTypes($select) {
    let types = getCached("transaction_types");
    if (!types) {
        types = await apiFetch("/reference/transaction_types");
        setCached("transaction_types", types);
    }
    const data = types.map(t => {
        ReferenceCache.saleTypes[t.transactioN_TYPE_ID] = t.transactioN_DESC;
        return {
            id: t.transactioN_TYPE_ID,
            text: t.transactioN_DESC,
        };
    });
    initSelect2($select, data, "Select Sale Type");
}

export async function loadHSCodes($select) {
    let items = getCached("item_codes");
    if (!items) {
        items = await apiFetch("/reference/item_codes");
        setCached("item_codes", items);
    }
    const data = items.map(item => {
        ReferenceCache.hsCodes[item.hS_CODE] = item.description;
        return {
            id: item.hS_CODE,
            text: `${item.hS_CODE} - ${item.description}`,
            description: item.description,
        };
    });
    initSelect2($select, data, "Search HS Code");
}