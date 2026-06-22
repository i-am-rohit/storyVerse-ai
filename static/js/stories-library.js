/**
 * StoryVerse AI — Stories Library
 * Search · filters · view modal · delete
 */

(function () {
    "use strict";

    const config = window.STORIES_LIBRARY;
    if (!config) return;

    const grid = document.getElementById("story-grid");
    const searchInput = document.getElementById("st-search");
    const audioFilter = document.getElementById("st-filter-audio");
    const sortSelect = document.getElementById("st-sort");
    const noResults = document.getElementById("st-no-results");
    const statButtons = document.querySelectorAll(".st-stat");
    const modal = document.getElementById("story-modal");
    const modalTitle = document.getElementById("modal-title");
    const modalMeta = document.getElementById("modal-meta");
    const modalSource = document.getElementById("modal-source");
    const modalBody = document.getElementById("modal-body");
    const modalEdit = document.getElementById("modal-edit");
    const modalAudio = document.getElementById("modal-audio");

    let sourceFilter = "all";
    let audioFilterValue = "all";

    function showToast(message, type) {
        const container = document.getElementById("toast-container");
        if (!container) return;
        const id = "toast-" + Date.now();
        const bg = type === "success" ? "text-bg-success" : "text-bg-danger";
        container.insertAdjacentHTML("beforeend", `
            <div id="${id}" class="toast align-items-center ${bg} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>`);
        const el = document.getElementById(id);
        const toast = new bootstrap.Toast(el, { delay: 4000 });
        toast.show();
        el.addEventListener("hidden.bs.toast", () => el.remove());
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function formatDate(iso) {
        try {
            return new Date(iso).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
            });
        } catch (_) {
            return iso;
        }
    }

    function getCards() {
        return grid ? Array.from(grid.querySelectorAll(".st-card")) : [];
    }

    function applyFilters() {
        if (!grid) return;

        const query = (searchInput?.value || "").trim().toLowerCase();
        let visible = 0;

        getCards().forEach((card) => {
            const title = card.dataset.title || "";
            const genre = card.dataset.genre || "";
            const language = card.dataset.language || "";
            const source = card.dataset.source || "";
            const audio = card.dataset.audio || "";

            const matchesSearch = !query || title.includes(query) || genre.includes(query) || language.includes(query);
            const matchesSource = sourceFilter === "all" || source === sourceFilter;
            const matchesAudio = audioFilterValue === "all" || audio === audioFilterValue;

            const show = matchesSearch && matchesSource && matchesAudio;
            card.classList.toggle("is-hidden", !show);
            if (show) visible += 1;
        });

        if (noResults) {
            noResults.classList.toggle("d-none", visible > 0);
        }
    }

    function applySort() {
        if (!grid || !sortSelect) return;

        const cards = getCards();
        const mode = sortSelect.value;

        cards.sort((a, b) => {
            if (mode === "title") {
                return (a.dataset.title || "").localeCompare(b.dataset.title || "");
            }
            const ta = parseInt(a.dataset.created || "0", 10);
            const tb = parseInt(b.dataset.created || "0", 10);
            return mode === "oldest" ? ta - tb : tb - ta;
        });

        cards.forEach((card) => grid.appendChild(card));
    }

    function setActiveStat(btn) {
        statButtons.forEach((b) => b.classList.remove("is-active"));
        if (btn) btn.classList.add("is-active");
    }

    function openModal() {
        modal?.classList.remove("d-none");
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        modal?.classList.add("d-none");
        document.body.style.overflow = "";
    }

    function sourceChipClass(label) {
        if (label === "Uploaded Book Summary") return "st-chip--uploaded";
        if (label === "Manual") return "st-chip--manual";
        return "st-chip--generated";
    }

    async function viewStory(id) {
        openModal();
        modalBody.innerHTML = '<div class="st-modal__loading"><div class="st-spinner"></div></div>';
        modalTitle.textContent = "Loading…";
        modalMeta.textContent = "";

        try {
            const url = config.urls.get.replace("{id}", id);
            const res = await fetch(url);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Could not load story.");

            const story = data.story;
            modalTitle.textContent = story.title;
            modalMeta.textContent = `${story.language} · ${story.genre} · ${story.age_group}${story.story_length ? " · " + story.story_length : ""} · ${story.word_count} words · ${formatDate(story.created_at)}`;
            modalSource.textContent = story.source;
            modalSource.className = `st-chip ${sourceChipClass(story.source)}`;

            let html = `<p>${escapeHtml(story.content)}</p>`;
            if (story.moral) {
                html += `<div class="st-modal__moral"><strong>Moral</strong><p class="mb-0">${escapeHtml(story.moral)}</p></div>`;
            }
            modalBody.innerHTML = html;

            modalEdit.href = `${config.urls.create}?story=${story.id}`;
            modalAudio.href = `${config.urls.audiobooks}?story=${story.id}`;
        } catch (err) {
            modalBody.innerHTML = `<p class="text-danger">${escapeHtml(err.message)}</p>`;
        }
    }

    async function deleteStory(id, card) {
        if (!confirm("Delete this story? This cannot be undone.")) return;

        try {
            const url = config.urls.delete.replace("{id}", id);
            const res = await fetch(url, {
                method: "POST",
                headers: { "X-CSRFToken": config.csrfToken },
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Delete failed.");

            card.remove();
            showToast(data.message || "Story deleted.", "success");
            applyFilters();

            if (!getCards().length) {
                window.location.reload();
            }
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    if (searchInput) {
        searchInput.addEventListener("input", applyFilters);
    }

    if (audioFilter) {
        audioFilter.addEventListener("change", () => {
            audioFilterValue = audioFilter.value;
            applyFilters();
        });
    }

    if (sortSelect) {
        sortSelect.addEventListener("change", () => {
            applySort();
            applyFilters();
        });
    }

    statButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            setActiveStat(btn);

            const src = btn.dataset.filterSource;
            const audio = btn.dataset.filterAudio;

            if (src) {
                sourceFilter = src;
                audioFilterValue = "all";
                if (audioFilter) audioFilter.value = "all";
            } else if (audio) {
                sourceFilter = "all";
                audioFilterValue = audio;
                if (audioFilter) audioFilter.value = audio;
            }

            applyFilters();
        });
    });

    document.addEventListener("click", (e) => {
        const viewBtn = e.target.closest("[data-action='view']");
        if (viewBtn) {
            viewStory(viewBtn.dataset.id);
            return;
        }

        const delBtn = e.target.closest("[data-action='delete']");
        if (delBtn) {
            const card = delBtn.closest(".st-card");
            deleteStory(delBtn.dataset.id, card);
            return;
        }

        if (e.target.closest("[data-close-modal]")) {
            closeModal();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeModal();
    });

    applySort();
    applyFilters();
})();
