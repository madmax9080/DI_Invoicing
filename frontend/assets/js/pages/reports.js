import { apiFetch } from "../api.js";
import { FYManager } from "../utils.js?v=9";
import { showToast} from "../toast.js"

const state = {
    invoices: [],
    filters: {
        status: "",
        buyer_name: "",
        date_from: "",
        date_to: "",
        month: ""
    },
    pagination: {
        page: 1,
        perPage: 10,
        total: 0,
        pages: 0
    }
};

function initReportsFY() {
    FYManager.init("globalFySelect");
}

function formatBuyerSales(value) {
    return Number(value || 0).toLocaleString("en", {
        notation: "compact",
        maximumFractionDigits: 1
    });
}

let buyerChart = null;
async function loadSalesByBuyerChart() {
    const fy = FYManager.get();
    const response =
        await apiFetch(`/reports/sales-by-buyer?fy=${fy}`);
    const labels = response.labels || [];
    const values = response.series || [];
    document.querySelector("#buyerChartFYLabel").textContent =
        response.fiscal_year;
    const options = {
        chart: {
            type: "bar",
            height: Math.max(300, labels.length * 34 + 70),
            toolbar: { show: false },
            zoom: { enabled: false },
            background: "transparent",
            foreColor: "#64748b",
            animations: {
                enabled: true,
                easing: "easeinout",
                speed: 500
            },
            dropShadow: { enabled: false }
        },
        series: [{
            name: "Sales",
            data: values.map((value, index) => ({
                x: labels[index],
                y: value
            }))
        }],
        colors: ["#009be5"],
        plotOptions: {
            bar: {
                horizontal: true,
                barHeight: "58%",
                borderRadius: 5,
                dataLabels: { position: "top" },
                distributed: false
            }
        },
        fill: {
            type: "gradient",
            gradient: {
                shade: "light",
                type: "horizontal",
                gradientToColors: ["#146e98"],
                stops: [0, 100],
                opacityFrom: 0.95,
                opacityTo: 0.78
            }
        },
        dataLabels: {
            enabled: true,
            formatter: formatBuyerSales,
            style: {
                colors: ["#146e98"],
                fontSize: "10px",
                fontWeight: 600
            },
            offsetX: 6,
            dropShadow: { enabled: false }
        },
        grid: {
            borderColor: "#e8eef5",
            strokeDashArray: 3,
            padding: { left: 8, right: 16, top: 4, bottom: 4 },
            xaxis: { lines: { show: true } },
            yaxis: { lines: { show: false } }
        },
        tooltip: {
            theme: "light",
            y: {
                formatter: value => "Rs. " + value.toLocaleString("en-PK")
            }
        },
        xaxis: {
            type: "numeric",
            min: 0,
            axisBorder: { show: false },
            axisTicks: { show: false },
            labels: {
                formatter: formatBuyerSales,
                style: {
                    colors: "#334155",
                    fontSize: "11px",
                    fontWeight: 500
                }
            }
        },
        yaxis: {
            axisBorder: { show: false },
            axisTicks: { show: false },
            labels: {
                style: {
                    colors: "#334155",
                    fontSize: "11px",
                    fontWeight: 500
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

function formatItemRate(val) {
    if (val === null || val === undefined || val === "") return "-";
    const numericValue = Number(val);
    if (!Number.isFinite(numericValue)) return val;
    return formatAmount(numericValue);
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
        if (state.filters.buyer_name)
            params.append("buyer_name", state.filters.buyer_name);
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
    state.filters.buyer_name = $("#filterBuyerName").val().trim();
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
        if (state.filters.buyer_name)
            params.append("buyer_name", state.filters.buyer_name);
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
                <td colspan="31"
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
    if (status === "cancelled")
        return `<span class="badge bg-secondary">Cancelled</span>`;
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

async function cancelInvoice(id) {
    if (!confirm(
        "Cancel this posted invoice? It will no longer be included in sales."
    )) return;
    try {
        await apiFetch(
            `/invoices/${id}/cancel`,
            { method: "POST" }
        );
        showToast(
            "Invoice cancelled successfully",
            "success"
        );
        await reload();
    }
    catch (err) {
        showToast(
            err.response?.detail || "Cancel failed",
            "error"
        );
    }
}

function renderRow(inv, item, index) {
    const canDelete =
        ["failed", "invalid", "validation_failed", "pending", "cancelled"]
        .includes(inv.status);
    const actionBtn = inv.status === "posted"
        ? `<button class="btn btn-outline-warning btn-sm cancel-btn"
                style="border-radius:10px;font-size:12px"
                data-id="${inv.id}"
                title="Cancel invoice"
                aria-label="Cancel invoice">
                <i class="bi bi-x-circle"></i>
           </button>`
        : canDelete
        ? `<button class="btn btn-outline-danger btn-sm delete-btn"
                style="border-radius:10px;font-size:12px"
                data-id="${inv.id}"
                title="Delete invoice"
                aria-label="Delete invoice">
                <i class="bi bi-trash3-fill"></i>
           </button>`
        : "-";
    const downloadBtn = 
        `<button class="btn btn-outline-danger btn-sm download-pdf" style="border-radius:10px;font-size:12px"
            data-id="${inv.id}"
            data-name="${inv.buyerBusinessName}">
            <i class="bi bi-file-pdf"></i>
        </button>`
    $("#reportsTableBody").append(`
        <tr>
            <td>${index}</td>
            <td>${actionBtn}</td>
            <td>${downloadBtn}</td>
            <td>${formatDate(inv.invoiceDate)}</td>
            <td>${inv.status === "posted" ? formatDate(inv.updated_at) : "-"}</td>
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
            <td>${formatItemRate(item?.itemRate)}</td>
            <td>${formatAmount(item?.salesTaxApplicable)}</td>
            <td>${formatAmount(item?.salesTaxWithheldAtSource)}</td>
            <td>${formatAmount(item?.extraTax)}</td>
            <td>${formatAmount(item?.furtherTax)}</td>
            <td>${formatAmount(item?.fedPayable)}</td>
            <td>${formatAmount(item?.tax236H)}</td>
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
    const { page, pages, perPage, total } = state.pagination;
    $("#paginationStart").text(
        total ? (page - 1) * perPage + 1 : 0
    );
    $("#paginationEnd").text(
        Math.min(page * perPage, total)
    );
    $("#paginationTotal").text(total);

    const visiblePages = new Set(pages ? [1, pages] : []);
    for (
        let visiblePage = Math.max(1, page - 2);
        visiblePage <= Math.min(pages, page + 2);
        visiblePage++
    ) {
        visiblePages.add(visiblePage);
    }

    let previousPage = 0;
    const pageButtons = [...visiblePages]
        .filter(visiblePage => visiblePage > 0)
        .sort((left, right) => left - right)
        .map(visiblePage => {
            const gap = visiblePage - previousPage;
            previousPage = visiblePage;
            const ellipsis = gap > 1
                ? '<li class="page-item disabled"><span class="page-link" aria-hidden="true">&hellip;</span></li>'
                : "";
            const active = visiblePage === page;
            return `${ellipsis}
                <li class="page-item${active ? " active" : ""}">
                    <button
                        class="page-link reports-page-btn"
                        type="button"
                        data-page="${visiblePage}"
                        ${active ? 'aria-current="page"' : ""}
                        aria-label="Page ${visiblePage}">
                        ${visiblePage}
                    </button>
                </li>
            `;
        })
        .join("");
    $("#reportsPageNumbers").html(pageButtons);
}

function resetFiltersUI() {
    $("#filterStatus").val("");
    $("#filterBuyerName").val("");
    $("#filterDateFrom").val("");
    $("#filterDateTo").val("");
    $("#filterMonth").val("");
    state.filters = {
        status: "",
        buyer_name: "",
        date_from: "",
        date_to: "",
        month: ""
    };
}

function binding() {
    $("#reportsPageNumbers")
        .off("click.reports")
        .on("click.reports", ".reports-page-btn", async function () {
            const page = Number($(this).data("page"));
            if (
                Number.isInteger(page)
                && page >= 1
                && page <= state.pagination.pages
                && page !== state.pagination.page
            ) {
                state.pagination.page = page;
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
        .off("click", ".cancel-btn")
        .on("click", ".cancel-btn", function () {
            const id = $(this).data("id");
            cancelInvoice(id);
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
    $("#reportsPageNumbers").off(".reports");
}