(() => {
    const menuToggle = document.querySelector(".menu-toggle");
    const navigation = document.querySelector("#primary-navigation");

    if (menuToggle && navigation) {
        const closeMenu = () => {
            menuToggle.setAttribute("aria-expanded", "false");
            menuToggle.setAttribute("aria-label", "Open navigation menu");
            navigation.classList.remove("is-open");
        };

        menuToggle.addEventListener("click", () => {
            const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
            menuToggle.setAttribute("aria-expanded", String(!isOpen));
            menuToggle.setAttribute(
                "aria-label",
                isOpen ? "Open navigation menu" : "Close navigation menu",
            );
            navigation.classList.toggle("is-open", !isOpen);
        });

        navigation.addEventListener("click", (event) => {
            if (event.target.closest("a, button")) {
                closeMenu();
            }
        });

        document.addEventListener("click", (event) => {
            if (
                menuToggle.getAttribute("aria-expanded") === "true"
                && !navigation.contains(event.target)
                && !menuToggle.contains(event.target)
            ) {
                closeMenu();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeMenu();
            }
        });
    }

    const overlay = document.querySelector("#processing-overlay");
    if (!overlay) {
        return;
    }

    const title = overlay.querySelector(".processing-title");
    const message = overlay.querySelector(".processing-message");

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (event.defaultPrevented) {
                return;
            }
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll("form[data-processing-title]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (event.defaultPrevented) {
                return;
            }
            if (form.dataset.submitting === "true") {
                event.preventDefault();
                return;
            }

            if (!form.reportValidity()) {
                return;
            }

            form.dataset.submitting = "true";
            title.textContent = form.dataset.processingTitle;
            message.textContent = form.dataset.processingMessage;
            overlay.hidden = false;
            overlay.setAttribute("aria-hidden", "false");
            document.body.classList.add("processing");

            const submitButton = event.submitter;
            if (submitButton instanceof HTMLButtonElement) {
                submitButton.disabled = true;
            }
        });
    });

    window.addEventListener("pageshow", () => {
        overlay.hidden = true;
        overlay.setAttribute("aria-hidden", "true");
        document.body.classList.remove("processing");
        document.querySelectorAll("form[data-submitting='true']").forEach((form) => {
            delete form.dataset.submitting;
            form.querySelectorAll("button:disabled").forEach((button) => {
                button.disabled = false;
            });
        });
    });
})();
