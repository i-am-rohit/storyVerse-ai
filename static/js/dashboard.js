/**
 * StoryVerse AI — Dashboard
 * Animated counters · Chart.js · Dark theme charts
 */

(function () {
    "use strict";

    const chartData = window.DASHBOARD_DATA;
    if (!chartData) return;

    Chart.defaults.color = "#94a3b8";
    Chart.defaults.borderColor = "rgba(255, 255, 255, 0.06)";
    Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    padding: 12,
                    usePointStyle: true,
                    pointStyle: "circle",
                    font: { size: 11 },
                },
            },
            tooltip: {
                backgroundColor: "rgba(12, 12, 26, 0.95)",
                borderColor: "rgba(255, 255, 255, 0.1)",
                borderWidth: 1,
                titleFont: { size: 13, weight: "600" },
                bodyFont: { size: 12 },
                padding: 12,
                cornerRadius: 8,
            },
        },
    };

    /* Animated Counters
       ================================================================== */
    function animateCounter(el) {
        const target = parseFloat(el.dataset.counter) || 0;
        const decimals = parseInt(el.dataset.decimals, 10) || 0;
        const duration = 1500;
        const startTime = performance.now();

        function easeOutQuart(t) {
            return 1 - Math.pow(1 - t, 4);
        }

        function tick(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const value = target * easeOutQuart(progress);

            el.textContent = decimals > 0
                ? value.toFixed(decimals)
                : Math.floor(value).toLocaleString();

            if (progress < 1) {
                requestAnimationFrame(tick);
            } else {
                el.textContent = decimals > 0
                    ? target.toFixed(decimals)
                    : target.toLocaleString();
            }
        }

        requestAnimationFrame(tick);
    }

    document.querySelectorAll("[data-counter]").forEach((el, i) => {
        setTimeout(() => animateCounter(el), i * 100);
    });

    /* Genre Distribution — Doughnut
       ================================================================== */
    const genreCtx = document.getElementById("genre-chart");
    if (genreCtx) {
        new Chart(genreCtx, {
            type: "doughnut",
            data: {
                labels: chartData.genre.labels,
                datasets: [{
                    data: chartData.genre.data,
                    backgroundColor: chartData.genre.colors,
                    borderColor: "#0a0a14",
                    borderWidth: 3,
                    hoverOffset: 8,
                }],
            },
            options: {
                ...chartOptions,
                cutout: "65%",
                plugins: {
                    ...chartOptions.plugins,
                    legend: {
                        ...chartOptions.plugins.legend,
                        position: "bottom",
                    },
                },
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 1200,
                    easing: "easeOutQuart",
                },
            },
        });
    }

    /* Monthly Stories — Bar
       ================================================================== */
    const monthlyCtx = document.getElementById("monthly-chart");
    if (monthlyCtx) {
        const gradient = monthlyCtx.getContext("2d").createLinearGradient(0, 0, 0, 240);
        gradient.addColorStop(0, "rgba(59, 130, 246, 0.8)");
        gradient.addColorStop(1, "rgba(139, 92, 246, 0.3)");

        new Chart(monthlyCtx, {
            type: "bar",
            data: {
                labels: chartData.monthly.labels,
                datasets: [{
                    label: "Stories",
                    data: chartData.monthly.data,
                    backgroundColor: gradient,
                    borderColor: "#3b82f6",
                    borderWidth: 1,
                    borderRadius: 6,
                    borderSkipped: false,
                }],
            },
            options: {
                ...chartOptions,
                plugins: {
                    ...chartOptions.plugins,
                    legend: { display: false },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 10 } },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            font: { size: 10 },
                        },
                        grid: { color: "rgba(255, 255, 255, 0.04)" },
                    },
                },
                animation: {
                    duration: 1200,
                    easing: "easeOutQuart",
                },
            },
        });
    }

    /* Language Usage — Polar Area
       ================================================================== */
    const languageCtx = document.getElementById("language-chart");
    if (languageCtx) {
        const langColors = [
            "rgba(0, 212, 255, 0.7)",
            "rgba(139, 92, 246, 0.7)",
            "rgba(29, 185, 84, 0.7)",
            "rgba(236, 72, 153, 0.7)",
            "rgba(245, 158, 11, 0.7)",
            "rgba(6, 182, 212, 0.7)",
        ];

        new Chart(languageCtx, {
            type: "polarArea",
            data: {
                labels: chartData.language.labels,
                datasets: [{
                    data: chartData.language.data,
                    backgroundColor: langColors.slice(0, chartData.language.labels.length),
                    borderColor: "#0a0a14",
                    borderWidth: 2,
                }],
            },
            options: {
                ...chartOptions,
                scales: {
                    r: {
                        grid: { color: "rgba(255, 255, 255, 0.06)" },
                        ticks: {
                            display: false,
                            stepSize: 1,
                        },
                        pointLabels: {
                            font: { size: 10 },
                            color: "#94a3b8",
                        },
                    },
                },
                plugins: {
                    ...chartOptions.plugins,
                    legend: {
                        ...chartOptions.plugins.legend,
                        position: "bottom",
                    },
                },
                animation: {
                    duration: 1200,
                    easing: "easeOutQuart",
                },
            },
        });
    }

    /* Stat card hover glow pulse
       ================================================================== */
    document.querySelectorAll(".dash-stat-card").forEach((card) => {
        card.addEventListener("mouseenter", () => {
            card.style.borderColor = "rgba(59, 130, 246, 0.2)";
        });
        card.addEventListener("mouseleave", () => {
            card.style.borderColor = "";
        });
    });
})();
