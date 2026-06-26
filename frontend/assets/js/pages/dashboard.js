import { apiFetch } from "../api.js";
import { FYManager } from "../utils.js";
import { formatCompactPKR } from "../utils.js";
const fontWeight = {style: {fontWeight: 400}};

const dashboardCache = new Map();
const CACHE_TTL = 120000; // 2 minutes
const EVENTS_NS = ".dashboard";
let initialized = false;

function getFY() {
    return localStorage.getItem("selectedFY") || "current";
}

function getCacheKey(base) {
    return `${base}:${getFY()}`;
}

function getCache(key) {
    const entry = dashboardCache.get(key);
    if (!entry) return null;
    if (Date.now() - entry.time > CACHE_TTL) {
        dashboardCache.delete(key);
        return null;
    }
    return entry.data;
}

function setCache(key, data) {
    dashboardCache.set(key, {
        data,
        time: Date.now()
    });
}

async function loadKPIs() {
    try {
        const cacheKey = getCacheKey("kpis");
        let data = getCache(cacheKey);
        if (!data) {
            data = await await apiFetch(
                `/dashboard/kpis?fy`
            );
            setCache(cacheKey, data);
        }
        // const data = await apiFetch(
        //     `/api/dashboard/kpis?fy`
        // );
        const kpis = [
            {
                title: "Total Revenue",
                value: formatCurrency(data.total_sales),
                subtitle: "Total sales amount of invoices",
                iconClass: "bi bi-currency-dollar",
                iconBgClass: "icon-blue",
                trend: getTrend("#2563eb")
            },
            {
                title: "Total Invoices",
                value: data.total_invoices,
                subtitle: "All posted invoices",
                iconClass: "bi bi-file-earmark-text",
                iconBgClass: "icon-purple",
                trend: getTrend("#8b5cf6")
            },
            {
                title: "Sale Invoices",
                value: data.total_sale_invoices,
                subtitle: "Invoices with type sale",
                iconClass: "bi bi-receipt",
                iconBgClass: "icon-green",
                trend: getTrend("#22c55e")
            },
            {
                title: "Debit Invoices",
                value: data.total_debit_invoices,
                subtitle: "Invoices with type debit",
                iconClass: "bi bi-file-earmark-medical",
                iconBgClass: "icon-orange",
                trend: getTrend("#f97316")
            }
        ];
        renderKPIs(kpis);
    } catch (e) {
        console.error("KPI load failed", e);
    }
}

function renderKPIs(kpis) {
    const container = $("#kpiRow");
    container.empty();
    kpis.forEach(kpi => {
        container.append(`
            <div class="col-xl-6 col-lg-6 col-md-6 col-sm-12">
                <div class="kpi-card">
                    <div class="kpi-icon-circle ${kpi.iconBgClass}">
                        <i class="${kpi.iconClass}"></i>
                    </div>
                    <div class="kpi-content">
                        <div class="kpi-title">
                            ${kpi.title}
                        </div>
                        <div class="kpi-value">
                            ${kpi.value}
                        </div>
                        <div class="kpi-subtitle">
                            ${kpi.subtitle}
                        </div>
                    </div>
                    <div class="kpi-trend">
                        ${kpi.trend || ""}
                    </div>
                </div>
            </div>
        `);
    });
}

function getTrend(color) {
    return `
        <svg width="60" height="40" viewBox="0 0 60 40">
            <polyline
                points="2,30 12,22 22,26 34,10 46,18 58,4"
                fill="none"
                stroke="${color}"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round">
            </polyline>
        </svg>
    `;
}

// function renderKPIs(kpis) {
//     const container = $("#kpiRow");
//     container.empty();
//     kpis.forEach(kpi => {
//         container.append(`
//             <div class="col-xl-3 col-lg-4 col-md-6 col-6">
//                 <div class="card-custom kpi-square" style="background: linear-gradient(to left, ${kpi.colorStart}, ${kpi.colorEnd}); color: ${kpi.textColor};">
//                     <div class="card-header-row">
//                         <div class="card-title ">
//                             ${kpi.title}
//                         </div>
//                         <div class="card-icon">
//                             ${kpi.icon ? `<img src="${kpi.icon}" class="kpi-icon-img">` : ""}
//                         </div>
//                     </div>
//                     <div class="card-value">
//                         ${kpi.value}
//                     </div>
//                     <div class="card-subtitle" style="color: ${kpi.subtitleColor || "#64748b"};">
//                         ${kpi.subtitle}
//                     </div>
//                 </div>
//             </div>
//         `);
//     });
// }

let monthlySalesChart = null;
async function loadMonthlySalesChart() {
    const cacheKey = getCacheKey("monthly-sales");
    let response = getCache(cacheKey);
    if (!response) {
        response = await apiFetch(
                `/dashboard/monthly-sales?fy`
            );
        setCache(cacheKey, response);
    }
    // response =
    //         await apiFetch(
    //             `/api/dashboard/monthly-sales?fy`
    //         );
    const data =
        response.data;
    const fiscalYear =
        response.fiscal_year;
    const monthNames =
        ["Jul","Aug","Sep","Oct","Nov","Dec",
         "Jan","Feb","Mar","Apr","May","Jun"];
    const labels =
        data.map(d =>
            `${monthNames[(d.month+5)%12]} ${d.year}`
        );
    const seriesData = data.map(d => d.total_sales);
    const maxValue = Math.max(...seriesData);
    const paddedMax = Math.ceil(maxValue * 1.1);
    if (monthlySalesChart) {
        monthlySalesChart.destroy();
    }
    document.querySelector(
        "#monthlySalesChart"
    ).innerHTML = "";
    monthlySalesChart =
        new ApexCharts(
            document.querySelector(
                "#monthlySalesChart"
            ),
            {
               chart: {
                    type: "area",
                    height: 320,
                    toolbar: { show: false },
                    zoom: { enabled: false },
                    animations: {
                        enabled: true,
                        easing: "easeinout",
                        speed: 500
                    },
                },
                colors:["#009be5"],
                title: {
                    text:
                        `(${fiscalYear})`,
                    align: "center",
                    style: {
                        fontSize: "13px",
                        fontWeight: fontWeight
                    }
                },
                annotations: {
                    points: [{
                        x: labels[labels.length - 1],
                        y: seriesData[seriesData.length - 1],
                        marker: {
                            size: 6,
                            fillColor: "#146e98"
                        },
                        label: {
                            borderColor: "#009be5",
                            style: {
                                background: "#146e98",
                                color: "#fff"
                            }
                        }
                    }]
                },
                series: [{
                    name: "Monthly Sales",
                    data: seriesData
                }],
                xaxis: {
                    categories: labels,
                    axisBorder: { show: false },
                    axisTicks: { show: false },
                    labels: {
                        style: {
                            colors: "#6f7d6c",
                            fontSize: "12px"
                        }
                    }
                },
                yaxis: {
                    min: 0,
                    max: paddedMax,
                    tickAmount: 5,
                    forceNiceScale: true,
                    labels: {
                        formatter: function(val) {
                            return formatCompactPKR(val);
                        }
                    }
                },
                stroke: {
                    curve: "smooth",
                    width: 3
                },
                fill: {
                    type: "gradient",
                    gradient: {
                        shade: "dark",
                        type: "vertical",
                        gradientToColors: ["#046593"],
                        stops: [0, 100]
                    }
                },
                grid: {
                    borderColor: "#f1f3f5",
                    strokeDashArray: 4,
                    padding: {
                        left: 10,
                        right: 10
                    }
                },
                markers: {
                    size: 4,
                    strokeWidth: 0,
                    hover: {
                        size: 6
                    }
                },
                tooltip: {
                    theme: "light",
                    y: {
                        formatter: val => "PKR." + val.toLocaleString()
                    }
                },
                dataLabels: {
                    enabled: false
                }
            }
        );
    monthlySalesChart.render();
}

let quarterlySalesChart = null;
async function loadQuarterlySalesChart(){
    const cacheKey = getCacheKey("quarterly-sales");
    let response = getCache(cacheKey);
    if (!response) {
        response = await apiFetch(
            `/dashboard/quarterly-sales?fy`
        );
        setCache(cacheKey, response);
    }
    // const response =
    //     await apifFetch(
    //         `/api/dashboard/quarterly-sales?fy`
    //     );
    const options = {
        chart:{
            type:"bar",
            height:320,
            toolbar:{show:false}
        },
        series:[{
            name:"Sales",
            data:response.series
        }],
        xaxis:{
            categories:response.labels
        },
        plotOptions:{
            bar: {
                    columnWidth: "40%",
                    distributed: false
                }
        },
        title:{
            text:`(${response.fiscal_year})`,
            align:"center",
            style: {
                fontSize: "13px",
                fontWeight: fontWeight
            }
        },
        yaxis:{
            labels:{
                formatter: function(val) {
                    return formatCompactPKR(val);
                }
            }
        },
        fill: {
                type: "gradient",
                gradient: {
                    shade: "dark",
                    type: "vertical",
                    gradientToColors: ["#015176"],
                    stops: [0, 100]
                }
            },
        tooltip:{
            y:{
                formatter:(val)=>
                    "Rs." + val.toLocaleString("en-PK")
            }
        },
        dataLabels: {
            enabled: false,
        },
        colors:["#009be5"]
    };
    const el =
        document.querySelector(
            "#quarterlySalesChart"
        );
    if(quarterlySalesChart){
        quarterlySalesChart.destroy();
    }
    document.querySelector(
        "#quarterlySalesChart"
    ).innerHTML = "";
    quarterlySalesChart =
        new ApexCharts(el, options);
    quarterlySalesChart.render();
}

let invoiceCountChart = null;
async function loadInvoiceCountChart() {
    const cacheKey = getCacheKey("invoice-count");
    let response = getCache(cacheKey);
    if (!response) {
        response = await apiFetch(
            `/dashboard/invoice-count-monthly?fy`
        );
        setCache(cacheKey, response);
    }
    // const response =
    //     await apiFetch(
    //         `/api/dashboard/invoice-count-monthly?fy`
    //     );
    const data =
        response.data;
    const fiscalYear =
        response.fiscal_year;
    const labels =
        data.map(d =>
            `${getMonthName(d.month)} ${d.year}`
        );
    const values =
        data.map(d =>
            d.count
        );
    if (invoiceCountChart)
        invoiceCountChart.destroy();
    const invoiceCountChartEl = document.querySelector(
        "#invoiceCountChart"
    );
    invoiceCountChartEl.innerHTML = "";
    invoiceCountChart =
        new ApexCharts(invoiceCountChartEl, {
            chart: {
                type: "area",
                height: 300,
                toolbar: { show: false },
                background: "transparent",
                fontFamily: "Inter, sans-serif",
                zoom: { enabled: false },
                animations: {
                    enabled: true,
                    easing: "easeout",
                    speed: 500
                }
            },
                title: {
                    text:
                        `(${fiscalYear})`,
                    align: "center",
                    style: {
                        fontSize: "13px",
                        fontWeight: fontWeight
                    }
                },
                annotations: {
                    points: [{
                        x: labels[labels.length - 1],
                        y: values[values.length - 1],
                        marker: {
                            size: 6,
                            fillColor: "#146e98"
                        },
                        label: {
                            borderColor: "#009be5",
                            style: {
                                background: "#146e98",
                                color: "#fff"
                            }
                        }
                    }]
                },
                series: [{
                    name: "Invoices",
                    data: values
                }],
                colors: ["#009be5"],
                stroke: {
                    curve: "smooth",
                    width: 2.5
                },
                fill: {
                    type: "gradient",
                    gradient: {
                        shade: "dark",
                        type: "vertical",
                        gradientToColors: ["#146e98"],
                        stops: [0, 100]
                    }
                },
                markers: {
                    size: 0,
                    hover: {
                        size: 5
                    }
                },
                grid: {
                    borderColor: "#f1f5f9",
                    strokeDashArray: 3,
                    padding: {
                        left: 5,
                        right: 10
                    }
                },
                xaxis: {
                    categories: labels,
                    axisBorder: { show: false },
                    axisTicks: { show: false },
                    labels: {
                        style: {
                            colors: "#94a3b8",
                            fontSize: "12px",
                            fontWeight: 500
                        }
                    }
                },
                yaxis: {
                    labels: {
                        style: {
                            colors: "#94a3b8",
                            fontSize: "12px"
                        },
                        formatter: val =>
                            val.toLocaleString()
                    }
                },
                dataLabels: {
                    enabled: false
                },
                tooltip: {
                    theme: "light",
                    style: {
                        fontSize: "13px"
                    },
                    marker: {
                        show: true
                    },
                    y: {
                        formatter: val =>
                            `${val.toLocaleString()} invoices`
                    }
                },
                states: {
                    hover: {
                        filter: {
                            type: "lighten",
                            value: 0.06
                        }
                    }
                }
            }
        );
    invoiceCountChart.render();
}

function forceLogout() {
    localStorage.clear();
    sessionStorage.clear();
    window.location.replace("/index.html");
}

function formatCurrency(val) {
    return "Rs." + Number(val || 0)
        .toLocaleString("en-PK", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
}

function getMonthName(month) {
    return [
        "Jan", "Feb", "Mar",
        "Apr", "May", "Jun",
        "Jul", "Aug", "Sep",
        "Oct", "Nov", "Dec"
    ][month - 1];
}

async function populateGlobalFYSelect() {
    const select =
        document.getElementById(
            "globalFySelect"
        );
    if (!select) return;
    const today = new Date();
    let currentFYStart =
        today.getMonth() >= 6
            ? today.getFullYear()
            : today.getFullYear() - 1;
    select.innerHTML = "";
    for (let i = 0; i < 3; i++) {
        const start =
            currentFYStart - i;
        const end =
            String(start + 1).slice(-2);
        const fy =
            `${start}-${end}`;
        const option =
            document.createElement("option");
        option.value = fy;
        option.textContent =
            `FY ${start}-${end}`;
        select.appendChild(option);
    }
}

async function initDashboardFY() {
    // FYManager.init("globalFySelect");
    loadMonthlySalesChart();
    loadQuarterlySalesChart();
    loadInvoiceCountChart();
}

async function loadDashboardCharts() {
    loadMonthlySalesChart();
    loadInvoiceCountChart();
    loadQuarterlySalesChart();
}

export async function initDashboard(){
    if (initialized) return;
    initialized = true;
    const clientId = localStorage.getItem("client_id");
    if (!clientId) {
        console.warn("No client selected yet");
        return;
    }
    await populateGlobalFYSelect();
    FYManager.init("globalFySelect");
    $(document).trigger("selectedFYChanged");
    bindEvents();
    await Promise.all([
        loadKPIs(),
        // loadClientInfo(clientId),
        initDashboardFY()
    ]);
}

function bindEvents() {
    $("#globalFySelect")
        .off("change.dashboard")
        .on("change.dashboard", handleFYChange);

    $("#logoutBtn")
        .off("click.dashboard")
        .on("click.dashboard", forceLogout);
}

function handleFYChange() {
    const fy = this.value;
    const currentFY =
        localStorage.getItem("selectedFY");
    if (fy === currentFY) {
        return;
    }
    FYManager.set(fy);
    dashboardCache.clear();
    loadKPIs();
    loadDashboardCharts();
    $(document).trigger("selectedFYChanged");
}

export function destroyDashboard() {
    initialized = false;
    $("#globalFySelect").off(".dashboard");
    $("#logoutBtn").off(".dashboard");
    if (monthlySalesChart) {
        monthlySalesChart.destroy();
        monthlySalesChart = null;
    }
    if (quarterlySalesChart) {
        quarterlySalesChart.destroy();
        quarterlySalesChart = null;
    }
    if (invoiceCountChart) {
        invoiceCountChart.destroy();
        invoiceCountChart = null;
    }
}