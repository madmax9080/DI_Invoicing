import { BuyerService } from "../services/buyer_service.js";
import { showToast } from "../toast.js";

let buyers = [];
let totalEntries = 0;
let skip = 0;
let limit = 10;

function getClientId() {
    const clientId =
        localStorage.getItem("client_id");
    if (
        !clientId ||
        clientId === "null" ||
        clientId === "undefined"
    ) {
        return null;
    }
    return clientId;
}

export async function initBuyers() {
    const clientId = getClientId();
    if (!clientId) {
        console.error(
            "Missing client_id"
        );
        return;
    }
    await loadBuyers();
    bindEvents();
}

function bindEvents() {
    $("#addBuyerBtn")
        .off("click")
        .on("click", function () {
            resetBuyerForm();
            $("#buyerModal").modal("show");
        });
    $("#saveBuyerBtn")
        .off("click")
        .on("click", saveBuyer);
    $(document)
        .off("click", ".edit-buyer-btn")
        .on(
            "click",
            ".edit-buyer-btn",
            handleEditBuyer
        );
    $(document)
        .off("click", ".delete-buyer-btn")
        .on(
            "click",
            ".delete-buyer-btn",
            handleDeleteBuyer
        );
    $("#searchBuyerBtn")
    .off("click")
    .on("click", async function () {
        skip = 0;
        await loadBuyers();
    });
    $("#resetBuyerBtn")
    .off("click")
    .on("click", async function () {
        $("#buyerSearchInput").val("");
        skip = 0;
        await loadBuyers();
    });
    $("#prevPageBtn")
    .off("click")
    .on("click", async function () {
        if (skip === 0) {
            return;
        }
        skip -= limit;
        await loadBuyers();
    });
    $("#nextPageBtn")
    .off("click")
    .on("click", async function () {
        if (skip + limit >= totalEntries) {
            return;
        }
        skip += limit;
        await loadBuyers();
    });   
}

export function destroyBuyers() {
    buyers = [];
}

async function loadBuyers() {
    try {
        const search =
            $("#buyerSearchInput")
                .val()
                ?.trim() || "";
        const response =
            await BuyerService.getBuyers({
                skip,
                limit,
                search
            });
        buyers = response.items || [];
        totalEntries = response.total || 0;
        renderBuyersTable();
        updatePagination();
    } catch (error) {
        console.error(
            "Failed to load buyers:",
            error
        );
    }
}

function updatePagination() {
    const start =
        totalEntries === 0
            ? 0
            : (skip + 1);
    const end =
        Math.min(skip + buyers.length, totalEntries)
    $("#paginationStart").text(start);
    $("#paginationEnd").text(end);
    $("#paginationTotal").text(totalEntries);
    $("#prevPageBtn").prop(
        "disabled",
        skip === 0
    );
    $("#nextPageBtn").prop(
        "disabled",
        end >= totalEntries
    );
}

function renderBuyersTable() {

    const tbody = document.getElementById(
        "buyersTableBody"
    );

    if (!tbody) {
        return;
    }

    if (!buyers.length) {

        tbody.innerHTML = `
            <tr>
                <td colspan="7">
                    No buyers found
                </td>
            </tr>
        `;

        return;
    }

    tbody.innerHTML = buyers.map(
        (buyer, index) => `

            <tr>

                <td>
                    ${skip + index + 1}
                </td>

                <td>
                    <div class="d-flex gap-2">

                        <button
                            class="
                                btn
                                btn-sm
                                btn-light
                                border
                                edit-buyer-btn
                            "
                            data-id="${buyer.id}"
                            title="Edit Buyer"
                        >
                            <i class="bi bi-pencil-square text-primary"></i>
                        </button>

                        <button
                            class="
                                btn
                                btn-sm
                                btn-light
                                border
                                delete-buyer-btn
                            "
                            data-id="${buyer.id}"
                            title="Delete Buyer"
                        >
                            <i class="bi bi-trash text-danger"></i>
                        </button>

                    </div>
                </td>

                <td>
                    ${buyer.ntn_cnic || ""}
                </td>

                <td>
                    ${buyer.name || ""}
                </td>

                <td>
                    ${buyer.province || ""}
                </td>

                <td>
                    ${buyer.address || ""}
                </td>

                <td>
                    ${buyer.buyer_registration_type || ""}
                </td>

            </tr>

        `
    ).join("");
}

async function saveBuyer() {
    const btn =
        document.getElementById(
            "saveBuyerBtn"
        );
    btn.disabled = true;
    btn.innerText = "Saving...";
    try {
        const buyerId =
            $("#buyerId").val();
        const payload = {
            ntn_cnic:
                $("#buyerNTN")
                    .val()
                    .trim(),
            name:
                $("#buyerName")
                    .val()
                    .trim(),
            province:
                $("#buyerProvince")
                    .val(),
            address:
                $("#buyerAddress")
                    .val()
                    .trim(),
            buyer_registration_type:
                $("#buyerRegistrationType")
                    .val()
        };
        for (const [key, value] of Object.entries(payload)) {
            if (!value) {
                showToast(
                    `${key} is required`,
                    "warning"
                );
                resetBtn();
                return;
            }
        }
        const ntn = payload.ntn_cnic;
        if (
            ntn.length !== 7 &&
            ntn.length !== 13
        ) {
            showToast(
                "Enter a valid registration number with 7 or 13 characters",
                "warning"
            );
            resetBtn();
            return;
        }
        if (!buyerId) {
            await BuyerService.createBuyer(
                payload
            );
            showToast(
                "Buyer created successfully",
                "success"
            );
        }
        else {
            await BuyerService.updateBuyer(
                buyerId,
                payload
            );
            showToast(
                "Buyer updated successfully",
                "success"
            );
        }
        $("#buyerModal").modal("hide");
        resetBuyerForm();
        await loadBuyers();
    } catch (error) {
        console.error(
            "Save buyer failed:",
            error
        );
        showToast(
            error.message ||
            "Failed to save buyer",
            "danger"
        );
    } finally {
        resetBtn();
    }
    function resetBtn() {
        btn.disabled = false;
        btn.innerText =
            "Save Buyer";
    }
}

function handleEditBuyer() {
    const buyerId =
        $(this).data("id");
    const buyer =
        buyers.find(
            b => b.id == buyerId
        );
    if (!buyer) {
        return;
    }
    $("#buyerId").val(
        buyer.id
    );
    $("#buyerNTN").val(
        buyer.ntn_cnic || ""
    );
    $("#buyerName").val(
        buyer.name || ""
    );
    $("#buyerProvince").val(
        buyer.province || "")
        .trigger("change");
    $("#buyerAddress").val(
        buyer.address || ""
    );
    $("#buyerRegistrationType")
    .val(
        buyer.buyer_registration_type || ""
    )
    .trigger("change");
    $("#buyerModal").modal("show");
}

async function handleDeleteBuyer() {
    const buyerId =
        $(this).data("id");
    const confirmed =
        confirm(
            "Delete this buyer?"
        );
    if (!confirmed) {
        return;
    }
    try {
        await BuyerService.deleteBuyer(
            buyerId
        );
        await loadBuyers();
    } catch (error) {
        console.error(
            "Delete buyer failed:",
            error
        );
    }
}

function resetBuyerForm() {
    $("#buyerForm")[0].reset();
    $("#buyerId").val("");
}