document.addEventListener("DOMContentLoaded", () => {
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach((alert) => {
        setTimeout(() => {
            const closeBtn = alert.querySelector(".btn-close");
            if (closeBtn) closeBtn.click();
        }, 5000);
    });

    document.querySelectorAll(".logout-form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.stopPropagation();
        });
    });
});
