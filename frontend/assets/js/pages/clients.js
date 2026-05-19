import { showToast } from "../toast.js";
import { apiFetch } from "../api.js";
import { PROVINCES, getProvinceTextById } from "../provinces.js";

const clientId = localStorage.getItem("client_id");
let originalClientData = null;
function loadProvinces() {
    const $province = $("#sellerProvince");
    $province.empty().append(`<option></option>`);
    PROVINCES.forEach(p => {
        $province.append(
            `<option value="${p.id}">${p.text}</option>`
        );
    });
}

async function loadClientProfile() {
    if (!clientId) return;
    try {
        const data =
            await apiFetch(`/clients/${clientId}`);
        originalClientData = data;
        $("#sellerName").val(data.name);
        $("#sellerNTNCNIC")
            .val(data.sellerNTNCNIC);
        $("#sellerBusinessName")
            .val(data.sellerBusinessName);
        const provinceText =
            getProvinceTextById(
                data.sellerProvince
            );
        $("#sellerProvinceText")
            .val(provinceText);
        $("#sellerProvince")
            .val(data.sellerProvince);
        $("#sellerFbrToken")
            .val(data.token);
        $("#sellerAddress")
            .val(data.sellerAddress);
    } catch (err) {
        console.error(
            "Load client profile failed:",
            err
        );
    }
}

function setEditMode(enabled) {
    $("#clientProfileForm input, #clientProfileForm textarea")
        .prop("disabled", !enabled);
    $("#provinceViewWrapper")
        .toggleClass("d-none", enabled);
    $("#provinceEditWrapper")
        .toggleClass("d-none", !enabled);
    $("#editClientBtn")
        .toggleClass("d-none", enabled);
    $("#cancelClientEditBtn")
        .toggleClass("d-none", !enabled);
    $("#clientSaveWrapper")
        .toggleClass("d-none", !enabled);
    if (enabled) {
        $("#sellerProvince")
            .prop("disabled", false);
        if ($("#sellerProvince")
            .hasClass("select2-hidden-accessible")) {
            $("#sellerProvince")
                .select2("destroy");
        }
        $("#sellerProvince").select2({
            placeholder: "Select Province",
            width: "100%",
            allowClear: true
        });
        $("#sellerProvince")
            .val(originalClientData.sellerProvince)
            .trigger("change");
    } else {
        if ($("#sellerProvince")
            .hasClass("select2-hidden-accessible")) {
            $("#sellerProvince")
                .select2("destroy");
        }
    }
}

function bindEvents() {
    $("#editClientBtn")
        .off("click")
        .on("click", function () {

            setEditMode(true);
        });
    $("#cancelClientEditBtn")
        .off("click")
        .on("click", async function () {

            if (originalClientData) {
                await loadClientProfile();
            }

            setEditMode(false);
        });
    $("#clientProfileForm")
        .off("submit")
        .on("submit", async function (e) {
            e.preventDefault();
            const payload = {
                name:
                    $("#sellerName").val().trim(),
                sellerNTNCNIC:
                    $("#sellerNTNCNIC").val().trim(),
                sellerBusinessName:
                    $("#sellerBusinessName").val().trim(),
                sellerProvince:
                    $("#sellerProvince").val(),
                token:
                    $("#sellerFbrToken").val().trim(),
                sellerAddress:
                    $("#sellerAddress").val().trim()
            };
            try {
                await apiFetch(
                    `/clients/${clientId}`,
                    {
                        method: "PUT",
                        body: payload
                    }
                );
                showToast(
                    "Client updated successfully",
                    "success"
                );
                localStorage.setItem(
                    "client_name",
                    payload.name
                );
                localStorage.setItem(
                    "client_business",
                    payload.sellerBusinessName
                );
                setEditMode(false);
                await loadClientProfile();
            } catch (err) {
                console.error(
                    "Update client failed:",
                    err
                );
            }
        });
}

export async function initClients() {
    loadProvinces();
    await loadClientProfile();
    setEditMode(false);
    bindEvents();
}

export function destroyClients() {
    $(document).off(".clients");
}