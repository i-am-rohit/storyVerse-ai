/**
 * StoryVerse AI — Book Summarizer
 * Drag & drop upload · Library · Per-book summary actions
 */

(function () {
    "use strict";

    const config = window.BOOK_SUMMARIZER;
    if (!config) return;

    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const dropzoneContent = document.getElementById("dropzone-content");
    const filePreview = document.getElementById("file-preview");
    const fileName = document.getElementById("file-name");
    const fileMeta = document.getElementById("file-meta");
    const fileIcon = document.getElementById("file-icon");
    const fileRemove = document.getElementById("file-remove");
    const uploadProgress = document.getElementById("upload-progress");
    const progressFill = document.getElementById("progress-fill");
    const progressText = document.getElementById("progress-text");
    const generationProgress = document.getElementById("generation-progress");
    const genProgressFill = document.getElementById("gen-progress-fill");
    const genProgressText = document.getElementById("gen-progress-text");
    const btnGenerate = document.getElementById("btn-generate");
    const btnFullBook = document.getElementById("btn-full-book");
    const btnChapters = document.getElementById("btn-chapters");
    const btnShortStories = document.getElementById("btn-short-stories");
    const quickActions = document.getElementById("quick-actions");
    const btnNarrate = document.getElementById("btn-narrate");
    const btnDownload = document.getElementById("btn-download");
    const emptyState = document.getElementById("empty-state");
    const summaryOutput = document.getElementById("summary-output");
    const summaryActions = document.getElementById("summary-actions");
    const summaryStatus = document.getElementById("summary-status");
    const shortSummary = document.getElementById("short-summary");
    const detailedSummary = document.getElementById("detailed-summary");
    const chapterList = document.getElementById("chapter-list");
    const chapterShortList = document.getElementById("chapter-short-list");
    const mainPointsList = document.getElementById("main-points-list");
    const shortStoriesList = document.getElementById("short-stories-list");
    const readingGuide = document.getElementById("reading-guide");
    const libraryEl = document.getElementById("book-library");
    const libraryEmpty = document.getElementById("library-empty");

    const ALLOWED = [".pdf", ".docx", ".txt"];
    const MAX_SIZE = 10 * 1024 * 1024;

    const ACTION_LABELS = {
        short: "Short Summary",
        detailed: "Full Book Summary",
        full_book: "Full Book Summary",
        main_points: "Main Points",
        chapters_short: "Chapter Wise",
        short_stories: "Short Stories",
        chapters: "Chapter Summaries",
        reading_guide: "Reading Guide",
        all: "All Options",
    };

    const TARGET_TAB = {
        short_summary: "tab-short",
        detailed_summary: "tab-detailed",
        reading_guide: "tab-reading",
        chapter_summaries: "tab-chapters",
        chapter_short_summaries: "tab-chapters-short",
        main_points: "tab-main-points",
        short_stories: "tab-short-stories",
    };

    const TAB_FOR_TYPE = {
        short: "tab-short",
        detailed: "tab-detailed",
        full_book: "tab-detailed",
        main_points: "tab-main-points",
        chapters_short: "tab-chapters-short",
        short_stories: "tab-short-stories",
        chapters: "tab-chapters",
        reading_guide: "tab-reading",
    };

    let currentFile = null;
    let documentId = null;
    let summaryId = null;
    let libraryDocs = [];

    const FILE_ICONS = {
        pdf: { class: "bs-file-icon--pdf", icon: "bi-file-pdf" },
        docx: { class: "bs-file-icon--docx", icon: "bi-file-word" },
        txt: { class: "bs-file-icon--txt", icon: "bi-file-text" },
    };

    function showToast(message, type) {
        const container = document.getElementById("toast-container");
        const id = "toast-" + Date.now();
        const bg = type === "success" ? "text-bg-success" : "text-bg-danger";
        container.insertAdjacentHTML("beforeend", `
            <div id="${id}" class="toast align-items-center ${bg} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto"
                            data-bs-dismiss="toast"></button>
                </div>
            </div>`);
        const el = document.getElementById(id);
        const toast = new bootstrap.Toast(el, { delay: 4000 });
        toast.show();
        el.addEventListener("hidden.bs.toast", () => el.remove());
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function formatDate(iso) {
        if (!iso) return "";
        try {
            return new Date(iso).toLocaleDateString(undefined, {
                month: "short", day: "numeric", year: "numeric",
            });
        } catch (_) {
            return "";
        }
    }

    function setStatus(text, state) {
        summaryStatus.textContent = text;
        summaryStatus.className = "bs-status badge";
        if (state) summaryStatus.classList.add(state);
    }

    function setLoading(btn, loading) {
        btn.disabled = loading;
        btn.classList.toggle("is-loading", loading);
    }

    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / 1048576).toFixed(1) + " MB";
    }

    function getExtension(name) {
        const dot = name.lastIndexOf(".");
        return dot >= 0 ? name.slice(dot).toLowerCase() : "";
    }

    function validateFile(file) {
        const ext = getExtension(file.name);
        if (!ALLOWED.includes(ext)) {
            showToast("Unsupported file type. Please upload PDF, DOCX, or TXT.", "error");
            return false;
        }
        if (file.size > MAX_SIZE) {
            showToast("File exceeds the 10 MB limit.", "error");
            return false;
        }
        return true;
    }

    function showFilePreview(file) {
        const ext = getExtension(file.name).replace(".", "");
        const iconData = FILE_ICONS[ext] || { class: "", icon: "bi-file-earmark" };

        dropzoneContent.classList.add("d-none");
        filePreview.classList.remove("d-none");
        dropzone.classList.add("has-file");

        fileName.textContent = file.name;
        fileMeta.textContent = `${ext.toUpperCase()} · ${formatBytes(file.size)}`;
        fileIcon.className = "bs-file-icon " + iconData.class;
        fileIcon.innerHTML = `<i class="bi ${iconData.icon}"></i>`;
    }

    function resetOutput() {
        emptyState.classList.remove("d-none");
        summaryOutput.classList.add("d-none");
        summaryActions.classList.add("d-none");
        setStatus("Waiting", "");
    }

    function showOutput() {
        emptyState.classList.add("d-none");
        summaryOutput.classList.remove("d-none");
        summaryActions.classList.remove("d-none");
    }

    const TARGET_FIELDS = {
        short_summary: shortSummary,
        detailed_summary: detailedSummary,
        reading_guide: readingGuide,
    };

    function showGenerationProgress(message, percent) {
        if (generationProgress) generationProgress.classList.remove("d-none");
        if (genProgressText) genProgressText.textContent = message || "Processing…";
        if (genProgressFill) genProgressFill.style.width = `${Math.min(100, percent || 0)}%`;
        setStatus("Generating", "is-generating");
    }

    function hideGenerationProgress() {
        if (generationProgress) generationProgress.classList.add("d-none");
        if (genProgressFill) genProgressFill.style.width = "0%";
    }

    function prepareStreamingOutput(type) {
        showOutput();
        const focus = type === "all" ? "short" : type;
        if (TAB_FOR_TYPE[focus]) {
            const tabBtn = document.getElementById(TAB_FOR_TYPE[focus]);
            if (tabBtn) bootstrap.Tab.getOrCreateInstance(tabBtn).show();
        }

        if (focus === "short" || focus === "full_book" || focus === "detailed" || focus === "reading_guide") {
            const field = focus === "short" ? shortSummary
                : focus === "reading_guide" ? readingGuide
                    : detailedSummary;
            if (field) field.textContent = "";
        }
    }

    function appendStreamToken(target, text) {
        if (!text) return;
        const el = TARGET_FIELDS[target];
        if (el) {
            el.textContent += text;
            el.scrollTop = el.scrollHeight;
        }
    }

    async function streamGenerate(docId, type) {
        if (!window.StoryVerseSSE) {
            throw new Error("Streaming client failed to load.");
        }

        let savedPayload = null;

        await window.StoryVerseSSE.postSse(
            config.urls.generate,
            { document_id: docId, type },
            {
                progress: (data) => {
                    showGenerationProgress(data.message, data.percent);
                    if (data.target && TARGET_TAB[data.target]) {
                        const tabBtn = document.getElementById(TARGET_TAB[data.target]);
                        if (tabBtn) bootstrap.Tab.getOrCreateInstance(tabBtn).show();
                    }
                },
                token: (data) => appendStreamToken(data.target, data.text),
                complete: () => {
                    showGenerationProgress("Saving summaries…", 99);
                },
                saved: (data) => {
                    savedPayload = data;
                },
                error: (data) => {
                    throw new Error(data.error || "Generation failed.");
                },
            },
            config.csrfToken,
        );

        return savedPayload;
    }

    function renderChapterCards(container, chapters) {
        container.innerHTML = "";
        if (!chapters || !chapters.length) {
            container.innerHTML = '<p class="bs-empty-inline">Not generated yet — use the action button for this book.</p>';
            return;
        }
        chapters.forEach((ch, i) => {
            const pct = ch.percent_of_book != null
                ? `<span class="bs-chapter-pct">${ch.percent_of_book}% of book</span>`
                : "";
            container.insertAdjacentHTML("beforeend", `
                <div class="bs-chapter-card">
                    <div class="bs-chapter-title">
                        <span class="bs-chapter-num">${i + 1}</span>
                        ${escapeHtml(ch.title)}
                        ${pct}
                    </div>
                    <p class="bs-chapter-text">${escapeHtml(ch.summary)}</p>
                    <div class="bs-chapter-words">${(ch.word_count || 0).toLocaleString()} words in section</div>
                </div>`);
        });
    }

    function renderMainPoints(container, points) {
        container.innerHTML = "";
        if (!points || !points.length) {
            container.innerHTML = '<p class="bs-empty-inline">Not generated yet — click <strong>Main Points</strong> for this book.</p>';
            return;
        }
        points.forEach((item) => {
            container.insertAdjacentHTML("beforeend", `
                <li class="bs-point-item">
                    <span class="bs-point-category">${escapeHtml(item.category || "Point")}</span>
                    <p class="bs-point-text">${escapeHtml(item.point || "")}</p>
                </li>`);
        });
    }

    function renderShortStories(container, stories) {
        container.innerHTML = "";
        if (!stories || !stories.length) {
            container.innerHTML = '<p class="bs-empty-inline">Not generated yet — click <strong>Short Stories</strong> for this book.</p>';
            return;
        }
        stories.forEach((story, i) => {
            container.insertAdjacentHTML("beforeend", `
                <article class="bs-story-card">
                    <div class="bs-story-header">
                        <h4 class="bs-story-title">${escapeHtml(story.title)}</h4>
                        ${story.source_chapter ? `<span class="bs-story-source">From ${escapeHtml(story.source_chapter)}</span>` : ""}
                    </div>
                    <p class="bs-story-content">${escapeHtml(story.content)}</p>
                    ${story.moral ? `<p class="bs-story-moral"><i class="bi bi-lightbulb"></i> ${escapeHtml(story.moral)}</p>` : ""}
                    <div class="bs-story-footer">
                        <span class="bs-story-words">${(story.word_count || 0).toLocaleString()} words</span>
                        <button type="button" class="bs-story-narrate" data-story-index="${i}">
                            <i class="bi bi-mic"></i> Narrate this story
                        </button>
                    </div>
                </article>`);
        });
    }

    function setQuickActionsEnabled(enabled) {
        btnGenerate.disabled = !enabled;
        if (btnFullBook) btnFullBook.disabled = !enabled;
        if (btnChapters) btnChapters.disabled = !enabled;
        if (btnShortStories) btnShortStories.disabled = !enabled;
        if (quickActions) quickActions.classList.toggle("d-none", !enabled);
    }

    function renderSummary(data, focusType) {
        summaryId = data.summary_id;
        documentId = data.document_id;

        shortSummary.textContent = data.short_summary || "Generate a short summary from your book library.";
        if (detailedSummary) {
            detailedSummary.textContent = data.detailed_summary || "Generate a full book summary from your book library.";
        }
        readingGuide.textContent = data.reading_guide || "Generate a reading guide from your book library.";

        renderChapterCards(chapterShortList, data.chapter_short_summaries);
        renderChapterCards(chapterList, data.chapter_summaries);
        renderMainPoints(mainPointsList, data.main_points);
        renderShortStories(shortStoriesList, data.short_stories);

        showOutput();
        setStatus("Ready", "is-ready");

        if (focusType && TAB_FOR_TYPE[focusType]) {
            const tabBtn = document.getElementById(TAB_FOR_TYPE[focusType]);
            if (tabBtn) bootstrap.Tab.getOrCreateInstance(tabBtn).show();
        }
    }

    function resetFile() {
        currentFile = null;
        documentId = null;
        summaryId = null;
        fileInput.value = "";
        dropzoneContent.classList.remove("d-none");
        filePreview.classList.add("d-none");
        dropzone.classList.remove("has-file");
        uploadProgress.classList.add("d-none");
        progressFill.style.width = "0%";
        setQuickActionsEnabled(false);
        resetOutput();
    }

    function selectDocument(doc) {
        documentId = doc.id;
        summaryId = doc.summary_id || null;
        showFilePreviewFromDoc(doc);
        setQuickActionsEnabled(true);
    }

    function showFilePreviewFromDoc(doc) {
        const iconData = FILE_ICONS[doc.file_type] || { class: "", icon: "bi-file-earmark" };
        dropzoneContent.classList.add("d-none");
        filePreview.classList.remove("d-none");
        dropzone.classList.add("has-file");
        fileName.textContent = doc.title;
        fileMeta.textContent = `${doc.file_type.toUpperCase()} · ${doc.word_count.toLocaleString()} words · ${doc.page_count} pages`;
        fileIcon.className = "bs-file-icon " + iconData.class;
        fileIcon.innerHTML = `<i class="bi ${iconData.icon}"></i>`;
        currentFile = { name: doc.title };
    }

    function renderLibrary() {
        if (!libraryEl) return;

        if (!libraryDocs.length) {
            libraryEl.innerHTML = "";
            if (libraryEmpty) libraryEmpty.classList.remove("d-none");
            return;
        }

        if (libraryEmpty) libraryEmpty.classList.add("d-none");

        libraryEl.innerHTML = libraryDocs.map((doc) => {
            const types = new Set(doc.summary_types || []);
            const badge = doc.has_summary
                ? `<span class="bs-lib-badge bs-lib-badge--ready">${doc.summary_types.length} ready</span>`
                : `<span class="bs-lib-badge">Not summarized</span>`;

            const btn = (type, icon) => {
                const done = types.has(type);
                return `<button type="button" class="bs-lib-action ${done ? "is-done" : ""}"
                    data-action="generate" data-id="${doc.id}" data-type="${type}" title="${ACTION_LABELS[type]}">
                    <i class="bi ${icon}"></i> ${ACTION_LABELS[type]}
                </button>`;
            };

            return `
                <article class="bs-lib-card ${documentId === doc.id ? "is-active" : ""}" data-id="${doc.id}">
                    <div class="bs-lib-main">
                        <h4 class="bs-lib-title">${escapeHtml(doc.title)}</h4>
                        <p class="bs-lib-meta">${doc.file_type.toUpperCase()} · ${doc.word_count.toLocaleString()} words · ${doc.page_count} pages</p>
                        <p class="bs-lib-date">${formatDate(doc.created_at)}</p>
                    </div>
                    <div class="bs-lib-side">
                        ${badge}
                        <div class="bs-lib-actions">
                            ${btn("full_book", "bi-book")}
                            ${btn("chapters", "bi-list-ol")}
                            ${btn("short_stories", "bi-journal-richtext")}
                            ${btn("short", "bi-lightning")}
                            ${btn("main_points", "bi-list-check")}
                            ${btn("chapters_short", "bi-lightning-charge")}
                            ${btn("reading_guide", "bi-signpost-split")}
                            ${btn("all", "bi-stars")}
                        </div>
                        <div class="bs-lib-actions bs-lib-actions--secondary">
                            ${doc.has_summary ? `
                                <button type="button" class="bs-lib-action bs-lib-action--view" data-action="view" data-id="${doc.id}">
                                    <i class="bi bi-eye"></i> View
                                </button>
                            ` : ""}
                            <button type="button" class="bs-lib-action bs-lib-action--delete" data-action="delete" data-id="${doc.id}">
                                <i class="bi bi-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                </article>`;
        }).join("");
    }

    async function loadLibrary() {
        if (!config.urls.documents) return;
        try {
            const res = await fetch(config.urls.documents);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);
            libraryDocs = data.documents || [];
            renderLibrary();
        } catch (_) {
            /* optional */
        }
    }

    async function loadDocumentSummary(docId, focusType) {
        const url = config.urls.document.replace("{id}", docId);
        const res = await fetch(url);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Could not load book.");

        selectDocument(data.document);
        if (data.summary) {
            renderSummary(data.summary, focusType);
        } else {
            resetOutput();
            setStatus("No summary yet", "");
        }
        return data;
    }

    async function generateForDocument(docId, type) {
        prepareStreamingOutput(type);
        showGenerationProgress("Starting…", 2);
        setLoading(btnGenerate, true);
        if (btnFullBook) setLoading(btnFullBook, true);
        if (btnChapters) setLoading(btnChapters, true);
        if (btnShortStories) setLoading(btnShortStories, true);

        try {
            const data = await streamGenerate(docId, type);
            if (!data) throw new Error("Generation finished without a result.");

            hideGenerationProgress();
            selectDocument(data.document);
            renderSummary(data.summary, type === "all" ? "short" : type);
            showToast(`${ACTION_LABELS[type] || "Summary"} ready!`, "success");
            await loadLibrary();
        } catch (err) {
            hideGenerationProgress();
            setStatus("Error", "");
            showToast(err.message, "error");
        } finally {
            setLoading(btnGenerate, false);
            if (btnFullBook) setLoading(btnFullBook, false);
            if (btnChapters) setLoading(btnChapters, false);
            if (btnShortStories) setLoading(btnShortStories, false);
        }
    }

    async function deleteDocument(docId) {
        if (!confirm("Delete this book and all its summaries?")) return;
        try {
            const url = config.urls.delete.replace("{id}", docId);
            const res = await fetch(url, {
                method: "DELETE",
                headers: { "X-CSRFToken": config.csrfToken },
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);

            if (documentId === docId) resetFile();
            showToast("Book deleted.", "success");
            await loadLibrary();
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);

        uploadProgress.classList.remove("d-none");
        progressFill.style.width = "30%";
        progressText.textContent = "Uploading…";
        setStatus("Uploading", "is-uploading");

        try {
            progressFill.style.width = "60%";
            const response = await fetch(config.urls.upload, {
                method: "POST",
                headers: { "X-CSRFToken": config.csrfToken },
                body: formData,
            });

            progressFill.style.width = "90%";
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Upload failed.");

            progressFill.style.width = "100%";
            progressText.textContent = "Upload complete!";
            selectDocument(data.document);
            setStatus("Ready", "");
            showToast(`"${data.document.title}" uploaded — choose an action below.`, "success");
            setTimeout(() => uploadProgress.classList.add("d-none"), 800);
            await loadLibrary();
        } catch (err) {
            uploadProgress.classList.add("d-none");
            setStatus("Error", "");
            showToast(err.message, "error");
            resetFile();
        }
    }

    function handleFile(file) {
        if (!validateFile(file)) return;
        currentFile = file;
        showFilePreview(file);
        uploadFile(file);
    }

    function getActiveSummaryType() {
        const active = document.querySelector("#summary-tabs .nav-link.active");
        if (!active) return "short";
        if (active.id === "tab-detailed") return "full_book";
        if (active.id === "tab-main-points") return "main_points";
        if (active.id === "tab-chapters") return "chapters";
        if (active.id === "tab-chapters-short") return "chapters_short";
        if (active.id === "tab-short-stories") return "short_stories";
        if (active.id === "tab-reading") return "reading_guide";
        return "short";
    }

    async function narrateStory(storyIndex) {
        if (!summaryId) {
            showToast("Generate short stories first.", "error");
            return;
        }

        setLoading(btnNarrate, true);

        try {
            const response = await fetch(config.urls.narrate, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": config.csrfToken,
                },
                body: JSON.stringify({
                    summary_id: summaryId,
                    type: "short_stories",
                    story_index: storyIndex,
                }),
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Narration failed.");

            showToast("Redirecting to Audiobook Studio…", "success");
            setTimeout(() => { window.location.href = data.redirect_url; }, 1000);
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            setLoading(btnNarrate, false);
        }
    }

    /* Drag & Drop */
    dropzone.addEventListener("click", (e) => {
        if (e.target.closest("#file-remove")) return;
        if (!currentFile) fileInput.click();
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length) handleFile(fileInput.files[0]);
    });

    ["dragenter", "dragover"].forEach((evt) => {
        dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            if (!currentFile) dropzone.classList.add("is-dragover");
        });
    });

    ["dragleave", "drop"].forEach((evt) => {
        dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropzone.classList.remove("is-dragover");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        if (currentFile) return;
        const files = e.dataTransfer.files;
        if (files.length) handleFile(files[0]);
    });

    fileRemove.addEventListener("click", (e) => {
        e.stopPropagation();
        resetFile();
    });

    btnGenerate.addEventListener("click", () => {
        if (!documentId) return;
        generateForDocument(documentId, "all");
    });

    if (btnFullBook) {
        btnFullBook.addEventListener("click", () => {
            if (!documentId) return;
            generateForDocument(documentId, "full_book");
        });
    }

    if (btnChapters) {
        btnChapters.addEventListener("click", () => {
            if (!documentId) return;
            generateForDocument(documentId, "chapters");
        });
    }

    if (btnShortStories) {
        btnShortStories.addEventListener("click", () => {
            if (!documentId) return;
            generateForDocument(documentId, "short_stories");
        });
    }

    if (libraryEl) {
        libraryEl.addEventListener("click", async (e) => {
            const btn = e.target.closest("[data-action]");
            if (!btn) return;
            const id = parseInt(btn.dataset.id, 10);
            const action = btn.dataset.action;

            if (action === "generate") {
                await generateForDocument(id, btn.dataset.type);
            } else if (action === "view") {
                try {
                    await loadDocumentSummary(id, "short");
                    document.querySelector(".bs-card-inner .bs-card-header")?.scrollIntoView({ behavior: "smooth" });
                } catch (err) {
                    showToast(err.message, "error");
                }
            } else if (action === "delete") {
                await deleteDocument(id);
            }
        });
    }

    if (shortStoriesList) {
        shortStoriesList.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-story-index]");
            if (!btn) return;
            narrateStory(parseInt(btn.dataset.storyIndex, 10));
        });
    }

    btnDownload.addEventListener("click", () => {
        if (!summaryId) {
            showToast("Generate a summary first.", "error");
            return;
        }
        const url = config.urls.download.replace("{id}", summaryId);
        const a = document.createElement("a");
        a.href = url;
        a.download = "";
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("Download started!", "success");
    });

    btnNarrate.addEventListener("click", async () => {
        if (!summaryId) {
            showToast("Generate a summary first.", "error");
            return;
        }

        setLoading(btnNarrate, true);

        try {
            const response = await fetch(config.urls.narrate, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": config.csrfToken,
                },
                body: JSON.stringify({
                    summary_id: summaryId,
                    type: getActiveSummaryType(),
                }),
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Narration failed.");

            showToast("Redirecting to Audiobook Studio…", "success");
            setTimeout(() => { window.location.href = data.redirect_url; }, 1000);
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            setLoading(btnNarrate, false);
        }
    });

    loadLibrary();
})();
