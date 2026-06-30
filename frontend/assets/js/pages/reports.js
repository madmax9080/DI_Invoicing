import { apiFetch } from "../api.js";
import { FYManager } from "../utils.js";
import { showToast} from "../toast.js"
import { formatCompactPKR } from "../utils.js";

const state = {
    invoices: [],
    filters: {
        status: "",
        date_from: "",
        date_to: "",
        month: ""
    },
    pagination: {
        page: 1,
        perPage: 25,
        total: 0,
        pages: 0
    }
};

function initReportsFY() {
    FYManager.init("globalFySelect");
}

let buyerChart = null;
async function loadSalesByBuyerChart() {
    const fy = FYManager.get();
    const response =
        await apiFetch(`/reports/sales-by-buyer?fy=${fy}`);
    const labels = response.labels || [];
    const values = response.series || [];
    document.querySelector(
        "#buyerChartFYLabel"
    ).textContent = response.fiscal_year;
    const maxValue = Math.max(...values, 0);
    const paddedMax = Math.ceil(maxValue * 1.9);
    const trackSeries =
        values.map(() => paddedMax);
    const options = {
        chart: {
            type: "bar",
            height: 360,
            stacked: true,
            stackType: "normal",
            offsetY: 0,
            toolbar: { show: false },
            zoom: { enabled: false },
            background: "transparent",
            foreColor: "#64748b",
            animations: {
                enabled: true,
                easing: "easeinout",
                speed: 500
            },
            dropShadow: {
                enabled: true,
                color: "#009be5",
                top: 8,
                blur: 12,
                opacity: 0.16
            }
        },
        series: [
            {
                name: "Sales",
                data: values
            },
            {
                name: "Track",
                data: trackSeries
            }
        ],
        colors: ["#009be5", "#e2e8f0"],
        plotOptions: {
            bar: {
                columnWidth: "34%",
                borderRadius: 8,
                distributed: false
            }
        },
        fill: {
            type: "gradient",
            gradient: {
                shade: "light",
                type: "vertical",
                gradientToColors: ["#146e98"],
                stops: [0, 100]
            }
        },
        dataLabels: { enabled: false },
        grid: {
            borderColor: "#e2e8f0",
            strokeDashArray: 4,
            padding: { bottom: 0 }
        },
        tooltip: {
            shared: false,
            intersect: true,
            y: {
                formatter: function(val, opts) {
                    if (opts.seriesIndex === 1)
                        return null;
                    return "Rs." + val.toLocaleString("en-PK");
                }
            }
        },
        xaxis: {
            categories: labels,
            axisBorder: { show: false },
            axisTicks: { show: false },
            labels: {
                style: {
                    colors: "#64748b",
                    fontSize: "12px"
                }
            }
        },
        yaxis: {
            min: 0,
            max: paddedMax,
            forceNiceScale: false,
            tickAmount: 5,
            axisBorder: { show: false },
            axisTicks: { show: false },
            labels: {
                formatter: function(val) {
                    return formatCompactPKR(val);
                },
                style: {
                    colors: "#64748b",
                    fontSize: "12px"
                }
            }
        },
        legend: { show: false },
    };
    const el =
        document.querySelector("#buyerSalesChart");
    if (buyerChart) {
        buyerChart.destroy();
        buyerChart = null;
    }
    el.innerHTML = "";
    buyerChart = new ApexCharts(el, options);
    await buyerChart.render();
}

function formatAmount(val) {
    return Number(val || 0).toLocaleString("en-PK", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2

    });
}

function formatDate(date) {
    if (!date) return "-";
    return new Date(date).toLocaleDateString();
}

function downloadFile(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => {
        window.URL.revokeObjectURL(url);
    }, 1000);
}

async function exportExcel() {
    try {
        const fy = FYManager.get();
        const params = new URLSearchParams();
        params.append("fy", fy);
        if (state.filters.status)
            params.append("status", state.filters.status);
        if (state.filters.date_from)
            params.append("date_from", state.filters.date_from);
        if (state.filters.date_to)
            params.append("date_to", state.filters.date_to);
        if (state.filters.month)
            params.append("month", state.filters.month);
        const blob = await apiFetch(
            `/reports/export/excel?${params.toString()}`,
            {
                responseType: "blob"
            }
        );
        downloadFile(
            blob,
            `Sales_Report_${fy}.xlsx`
        );
    }
    catch (err) {
        // console.error(err);
    }
}

let isDownloading = false;
async function downloadInvoicePDF(invoiceId, buyerBusinessName) {
    if (isDownloading) return;
    isDownloading = true;
    try {
        const blob = await apiFetch(
            `/reports/pdf/${invoiceId}`,
            {
                responseType: "blob"
            }
        );
        downloadFile(blob, `${buyerBusinessName}.pdf`);
    }
    catch (err) {
        // console.error(err);
    }
    finally {
        isDownloading = false;
    }
}

$("#exportExcelBtn").click(() => {
    exportExcel();
});

function readFilters() {
    state.filters.status = $("#filterStatus").val();
    state.filters.date_from = $("#filterDateFrom").val();
    state.filters.date_to = $("#filterDateTo").val();
    state.filters.month = $("#filterMonth").val();
}

async function fetchReports() {
    try {
        const fy = FYManager.get();
        const params = new URLSearchParams();
        params.append("fy", fy);
        params.append("page", state.pagination.page);
        params.append("per_page", state.pagination.perPage);
        if (state.filters.status)
            params.append("status", state.filters.status);
        if (state.filters.date_from)
            params.append("date_from", state.filters.date_from);
        if (state.filters.date_to)
            params.append("date_to", state.filters.date_to);
        if (state.filters.month)
            params.append("month", state.filters.month);
        const res =
            await apiFetch(`/reports/invoices?${params}`);
        // console.log("Reports:", res);
        state.invoices = res.data || [];
        state.pagination.total = res.total || 0;
        state.pagination.pages = res.pages || 0;
    }
    catch (err) {
        // console.error(err);
    }
}

function renderTable() {
    const tbody = $("#reportsTableBody");
    tbody.empty();
    if (!state.invoices.length) {
        tbody.append(`
            <tr>
                <td colspan="28"
                    class="text-center text-muted py-4">
                    <<<<<< No invoices found >>>>>>
                </td>
            </tr>
        `);
        return;
    }
    let index =
        (state.pagination.page - 1)
        * state.pagination.perPage + 1;
    state.invoices.forEach(inv => {
        if (!inv.items?.length) {
            renderRow(inv, null, index++);
        }
        else {
            inv.items.forEach(item => {
                renderRow(inv, item, index++);
            });
        }
    });
}

function renderStatusBadge(status) {
    if (status === "posted")
        return `<span class="badge bg-success">Posted</span>`;
    if (status === "failed"
        || status === "invalid")
        return `<span class="badge bg-danger">Failed</span>`;
    return `<span class="badge bg-warning text-dark">
                ${status}
            </span>`;
}

async function deleteInvoice(id) {
    if (!confirm(
        "Are you sure you want to delete this invoice?"
    )) return;
    try {
        await apiFetch(
            `/invoices/${id}`,
            { method: "DELETE" }
        );
        showToast(
            "Invoice deleted successfully",
            "success"
        );
        await reload();
    }
    catch (err) {
        // console.error(err);
        showToast(
            err.response?.detail || "Delete failed",
            "error"
        );
    }
}

function renderRow(inv, item, index) {
    const canDelete =
        ["failed", "invalid", "validation_failed", "pending"]
        .includes(inv.status);
    const deleteBtn =
        canDelete
        ? `<button class="btn btn-outline-danger btn-sm delete-btn"
                data-id="${inv.id}">
                <i class="bi bi-trash"></i>
           </button>`
        : "-";
    const downloadBtn = 
        `<button class="btn btn-outline-danger btn-sm download-pdf" style=border-radius:10px;font-size:12px
            data-id="${inv.id}"
            data-name="${inv.buyerBusinessName}">
            <i class="bi bi-file-pdf"></i>
        </button>`
    $("#reportsTableBody").append(`
        <tr>
            <td>${index}</td>
            <td>${deleteBtn}</td>
            <td>${downloadBtn}</td>
            <td>${formatDate(inv.invoiceDate)}</td>
            <td>${formatDate(inv.created_at)}</td>
            <td>${inv.fbrInvoiceNo || "-"}</td>
            <td>${inv.internal_invoice_no || "-"}</td>
            <td>${inv.invoiceRefNo || "-"}</td>
            <td>${inv.buyerBusinessName || "-"}</td>
            <td>${inv.buyerNTNCNIC || "-"}</td>
            <td>${inv.buyerRegistrationType || "-"}</td>
            <td>
                ${renderStatusBadge(inv.status)}
            </td>
            <td>${item?.hsCode || "-"}</td>
            <td>${item?.productDescription || "-"}</td>
            <td>${item?.uom || "-"}</td>
            <td>${item?.quantity || 0}</td>
            <td>${item?.saleType || "-"}</td>
            <td>${formatAmount(item?.valueSalesExcludingST)}</td>
            <td>${item?.fixedNotifiedValueOrRetailPrice || "-"}</td>
            <td>${item?.rate || "-"}</td>
            <td>${formatAmount(item?.salesTaxApplicable)}</td>
            <td>${formatAmount(item?.salesTaxWithheldAtSource)}</td>
            <td>${formatAmount(item?.extraTax)}</td>
            <td>${formatAmount(item?.furtherTax)}</td>
            <td>${formatAmount(item?.fedPayable)}</td>
            <td>${formatAmount(item?.discount)}</td>
            <td>${item?.sroScheduleNo || "-"}</td>
            <td>${item?.sroItemSerialNo || "-"}</td>
            <td class="fw-semibold">
                ${formatAmount(item?.totalValues)}
            </td>
        </tr>
    `);
}

function renderPagination() {
    $("#paginationStart").text(
        (state.pagination.page - 1)
        * state.pagination.perPage + 1
    );
    $("#paginationEnd").text(
        Math.min(
            state.pagination.page
            * state.pagination.perPage,
            state.pagination.total
        )
    );
    $("#paginationTotal").text(
        state.pagination.total
    );
}

function resetFiltersUI() {
    $("#filterStatus").val("");
    $("#filterDateFrom").val("");
    $("#filterDateTo").val("");
    $("#filterMonth").val("");
    state.filters = {
        status: "",
        date_from: "",
        date_to: "",
        month: ""
    };
}

function binding() {
    $("#prevPageBtn")
        .off("click")
        .on("click", async () => {
            if (state.pagination.page > 1) {
                state.pagination.page--;
                await reload();
            }
        });
    $("#nextPageBtn")
        .off("click")
        .on("click", async () => {
            if (state.pagination.page < state.pagination.pages) {
                state.pagination.page++;
                await reload();
            }
        });
}

async function reload() {
    readFilters();
    await fetchReports();
    renderTable();
    renderPagination();
}

// export function initReports() {
//     initReportsFY();
//     loadSalesByBuyerChart();
//     $("#globalFySelect")
//         .off("change.reports")
//         .on(
//             "change.reports",
//             loadSalesByBuyerChart
//     );
//      binding();
//     $("#applyFiltersBtn").click(() => {
//         state.pagination.page = 1;
//         reload();
//     });
//     $("#resetFiltersBtn")
//         .off("click")
//         .on("click", async () => {
//             resetFiltersUI();
//             await reload();
//         });
//     $(document)
//         .off("click", ".delete-btn")
//         .on("click", ".delete-btn", function () {
//             const id =
//                 $(this).data("id");

//             deleteInvoice(id);
//         });
//     $(document)
//     .off("click", ".download-pdf")
//     .on("click", ".download-pdf", function () {
//         const id = $(this).data("id");
//         const name = $(this).data("name");
//         downloadInvoicePDF(id, name);
//     });
//     reload();
// }   

export async function initReports() {
    initReportsFY();
    if (buyerChart) {
        buyerChart.destroy();
        buyerChart = null;
    }
    await loadSalesByBuyerChart();
    $("#globalFySelect")
        .off("change.reports")
        .on(
            "change.reports",
            async function () {
                if (buyerChart) {
                    buyerChart.destroy();
                    buyerChart = null;
                }
                await loadSalesByBuyerChart();
            }
        );
    binding();
    $("#applyFiltersBtn")
        .off("click")
        .on("click", async () => {
            state.pagination.page = 1;
            await reload();
        });
    $("#resetFiltersBtn")
        .off("click")
        .on("click", async () => {
            resetFiltersUI();
            await reload();
        });
    $(document)
        .off("click", ".delete-btn")
        .on("click", ".delete-btn", function () {
            const id = $(this).data("id");
            deleteInvoice(id);
        });
    $(document)
        .off("click", ".download-pdf")
        .on("click", ".download-pdf", function () {
            const id = $(this).data("id");
            const name = $(this).data("name");
            downloadInvoicePDF(id, name);
        });
    await reload();
}

export function destroyReports() {
    $(document).off(".reports");
}