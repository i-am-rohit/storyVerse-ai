/**
 * StoryVerse AI — Story Generator
 * Typing effect · AJAX actions · Toast notifications
 */

(function () {
    "use strict";

    const config = window.STORY_GENERATOR;
    if (!config) return;

    const form = document.getElementById("story-form");
    const emptyState = document.getElementById("empty-state");
    const storyOutput = document.getElementById("story-output");
    const storyActions = document.getElementById("story-actions");
    const typingIndicator = document.getElementById("typing-indicator");
    const typingText = document.getElementById("typing-text");
    const storyStatus = document.getElementById("story-status");
    const generationProgress = document.getElementById("generation-progress");
    const progressFill = document.getElementById("sg-progress-fill");
    const progressMsg = document.getElementById("sg-progress-msg");

    const titleEl = document.getElementById("story-title");
    const metaEl = document.getElementById("story-meta");
    const contentEl = document.getElementById("story-content");
    const moralEl = document.getElementById("story-moral");

    const btnGenerate = document.getElementById("btn-generate");
    const btnContinue = document.getElementById("btn-continue");
    const btnSave = document.getElementById("btn-save");
    const btnAudio = document.getElementById("btn-audio");

    let currentStory = null;
    let savedStoryId = null;
    let typingTimer = null;
    let isTyping = false;

    const genreLabels = {};
    const ageLabels = {};
    const langLabels = {};
    const lengthLabels = {};

    document.querySelectorAll("#genre option").forEach((o) => { genreLabels[o.value] = o.text; });
    document.querySelectorAll("#age_group option").forEach((o) => { ageLabels[o.value] = o.text; });
    document.querySelectorAll("#language option").forEach((o) => { langLabels[o.value] = o.text; });
    document.querySelectorAll("#story_length option").forEach((o) => { lengthLabels[o.value] = o.text; });

    function getFormData() {
        return {
            language: document.getElementById("language").value,
            genre: document.getElementById("genre").value,
            age_group: document.getElementById("age_group").value,
            story_length: document.getElementById("story_length").value,
            prompt: document.getElementById("prompt").value.trim(),
        };
    }

    function setStatus(text, state) {
        storyStatus.textContent = text;
        storyStatus.className = "sg-status badge";
        if (state) storyStatus.classList.add(state);
    }

    function setLoading(btn, loading) {
        btn.disabled = loading;
        btn.classList.toggle("is-loading", loading);
    }

    function setActionButtons(enabled) {
        btnContinue.disabled = !enabled || isTyping;
        btnSave.disabled = !enabled || isTyping;
        btnAudio.disabled = !enabled || isTyping || !savedStoryId;
    }

    async function apiPost(url, payload) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": config.csrfToken,
            },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Something went wrong.");
        }
        return data;
    }

    function showToast(message, type) {
        const container = document.getElementById("toast-container");
        const id = "toast-" + Date.now();
        const bgClass = type === "success" ? "text-bg-success" : "text-bg-danger";

        container.insertAdjacentHTML("beforeend", `
            <div id="${id}" class="toast align-items-center ${bgClass} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto"
                            data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `);

        const toastEl = document.getElementById(id);
        const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
        toast.show();
        toastEl.addEventListener("hidden.bs.toast", () => toastEl.remove());
    }

    function renderMeta(story) {
        const words = story.word_count || (story.content ? story.content.split(/\s+/).length : 0);
        const sizeLabel = lengthLabels[story.story_length] || story.story_length || "";
        metaEl.innerHTML = `
            <span class="sg-meta-tag"><i class="bi bi-bookmark"></i> ${genreLabels[story.genre] || story.genre}</span>
            <span class="sg-meta-tag"><i class="bi bi-people"></i> ${ageLabels[story.age_group] || story.age_group}</span>
            <span class="sg-meta-tag"><i class="bi bi-translate"></i> ${langLabels[story.language] || story.language}</span>
            ${sizeLabel ? `<span class="sg-meta-tag"><i class="bi bi-text-paragraph"></i> ${sizeLabel}</span>` : ""}
            ${words ? `<span class="sg-meta-tag"><i class="bi bi-fonts"></i> ${words} words</span>` : ""}
        `;
    }

    function typeText(element, text, speed, callback) {
        clearTimeout(typingTimer);
        isTyping = true;
        setActionButtons(false);

        element.textContent = "";
        element.classList.add("typing");

        let index = 0;
        const chars = text.split("");

        function tick() {
            if (index < chars.length) {
                element.textContent += chars[index];
                index++;
                typingTimer = setTimeout(tick, speed);
            } else {
                element.classList.remove("typing");
                isTyping = false;
                setActionButtons(true);
                if (callback) callback();
            }
        }

        tick();
    }

    function showOutput() {
        emptyState.classList.add("d-none");
        storyOutput.classList.remove("d-none");
        storyActions.classList.remove("d-none");
    }

    function showGenerating(message) {
        typingIndicator.classList.remove("d-none");
        if (typingText) typingText.textContent = message || "AI is writing your story…";
        setStatus("Generating", "is-generating");
    }

    function showProgress(message, percent) {
        if (generationProgress) generationProgress.classList.remove("d-none");
        if (progressMsg) progressMsg.textContent = message || "Processing…";
        if (progressFill) progressFill.style.width = `${Math.min(100, percent || 0)}%`;
        if (typingText) typingText.textContent = message || "AI is writing your story…";
    }

    function hideProgress() {
        if (generationProgress) generationProgress.classList.add("d-none");
        if (progressFill) progressFill.style.width = "0%";
    }

    function hideGenerating() {
        typingIndicator.classList.add("d-none");
        hideProgress();
    }

    async function streamPost(url, payload, handlers) {
        if (!window.StoryVerseSSE) {
            throw new Error("Streaming client failed to load.");
        }
        await window.StoryVerseSSE.postSse(url, payload, handlers, config.csrfToken);
    }

    function displayStory(story, animateContent) {
        currentStory = { ...story, prompt: getFormData().prompt };
        savedStoryId = null;
        btnAudio.disabled = true;

        showOutput();
        titleEl.textContent = story.title;
        renderMeta(story);
        moralEl.textContent = story.moral;

        if (animateContent) {
            typeText(contentEl, story.content, 12, () => {
                setStatus("Ready", "is-ready");
            });
        } else {
            contentEl.textContent = story.content;
            setStatus("Ready", "is-ready");
            setActionButtons(true);
        }
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const formData = getFormData();
        if (!formData.prompt) {
            showToast("Please enter a story prompt.", "error");
            document.getElementById("prompt").focus();
            return;
        }

        setLoading(btnGenerate, true);
        showGenerating();
        showProgress("Starting story generation…", 2);
        showOutput();
        contentEl.textContent = "";
        moralEl.textContent = "";
        titleEl.textContent = "Generating…";
        setActionButtons(false);
        isTyping = true;

        let streamedText = "";
        let finalStory = null;

        try {
            await streamPost(config.urls.generate, formData, {
                progress: (data) => {
                    showProgress(data.message, data.percent);
                },
                token: (data) => {
                    streamedText += data.text || "";
                    contentEl.textContent = streamedText;
                    contentEl.scrollTop = contentEl.scrollHeight;
                },
                complete: (data) => {
                    finalStory = data.story;
                },
                error: (data) => {
                    throw new Error(data.error || "Generation failed.");
                },
            });

            hideGenerating();
            if (finalStory) {
                isTyping = false;
                displayStory(finalStory, false);
            } else if (streamedText) {
                isTyping = false;
                displayStory({
                    title: formData.prompt.slice(0, 60) || "Untitled Story",
                    content: streamedText,
                    moral: "",
                    ...formData,
                }, false);
            }
        } catch (err) {
            hideGenerating();
            isTyping = false;
            setStatus("Error", "");
            showToast(err.message, "error");
            if (!currentStory) {
                storyOutput.classList.add("d-none");
                storyActions.classList.add("d-none");
                emptyState.classList.remove("d-none");
            }
        } finally {
            setLoading(btnGenerate, false);
        }
    });

    btnContinue.addEventListener("click", async () => {
        if (!currentStory || isTyping) return;

        setLoading(btnContinue, true);
        showGenerating("Continuing your story…");
        showProgress("Preparing continuation…", 5);
        isTyping = true;
        setActionButtons(false);

        let streamedText = "";
        let finalContent = null;

        try {
            await streamPost(config.urls.continue, {
                title: currentStory.title,
                content: currentStory.content,
                genre: currentStory.genre,
                age_group: currentStory.age_group,
                language: currentStory.language,
                story_length: currentStory.story_length || getFormData().story_length,
            }, {
                progress: (data) => showProgress(data.message, data.percent),
                token: (data) => {
                    streamedText += data.text || "";
                    contentEl.textContent = `${currentStory.content}\n\n${streamedText}`;
                },
                complete: (data) => {
                    finalContent = data.content;
                },
                error: (data) => {
                    throw new Error(data.error || "Continue failed.");
                },
            });

            currentStory.content = finalContent || streamedText || currentStory.content;
            savedStoryId = null;
            btnAudio.disabled = true;
            hideGenerating();
            contentEl.textContent = currentStory.content;
            isTyping = false;
            setActionButtons(true);
            setStatus("Continued", "is-ready");
        } catch (err) {
            hideGenerating();
            isTyping = false;
            showToast(err.message, "error");
        } finally {
            setLoading(btnContinue, false);
        }
    });

    btnSave.addEventListener("click", async () => {
        if (!currentStory || isTyping) return;

        setLoading(btnSave, true);

        try {
            const data = await apiPost(config.urls.save, {
                story_id: savedStoryId,
                title: currentStory.title,
                content: currentStory.content,
                moral: currentStory.moral,
                language: currentStory.language,
                genre: currentStory.genre,
                age_group: currentStory.age_group,
                story_length: currentStory.story_length || getFormData().story_length,
                prompt: currentStory.prompt,
            });

            savedStoryId = data.story_id;
            btnAudio.disabled = false;
            setStatus("Saved", "is-saved");
            showToast(data.message, "success");
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            setLoading(btnSave, false);
        }
    });

    btnAudio.addEventListener("click", async () => {
        if (!savedStoryId || isTyping) {
            showToast("Please save the story before converting to audio.", "error");
            return;
        }

        setLoading(btnAudio, true);

        try {
            const data = await apiPost(config.urls.convertAudio, {
                story_id: savedStoryId,
            });
            showToast(data.message, "success");
            if (data.redirect_url) {
                setTimeout(() => { window.location.href = data.redirect_url; }, 1200);
            }
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            setLoading(btnAudio, false);
        }
    });

    async function loadStoryFromUrl() {
        const storyId = new URLSearchParams(window.location.search).get("story");
        if (!storyId || !config.urls.get) return;

        try {
            const res = await fetch(config.urls.get.replace("{id}", storyId));
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Could not load story.");

            const story = data.story;
            if (story.language) document.getElementById("language").value = story.language;
            if (story.genre) document.getElementById("genre").value = story.genre;
            if (story.age_group) document.getElementById("age_group").value = story.age_group;
            if (story.story_length) document.getElementById("story_length").value = story.story_length;

            savedStoryId = story.id;
            currentStory = {
                title: story.title,
                content: story.content,
                moral: story.moral || "",
                language: story.language || document.getElementById("language").value,
                genre: story.genre || document.getElementById("genre").value,
                age_group: story.age_group || document.getElementById("age_group").value,
                story_length: story.story_length || document.getElementById("story_length").value,
                word_count: story.word_count,
                prompt: story.prompt || "",
            };

            emptyState.classList.add("d-none");
            storyOutput.classList.remove("d-none");
            storyActions.classList.remove("d-none");
            titleEl.textContent = story.title;
            contentEl.textContent = story.content;
            moralEl.textContent = story.moral || "";
            document.getElementById("story-moral-wrapper").classList.toggle("d-none", !story.moral);
            renderMeta(currentStory);
            setStatus("Loaded", "is-saved");
            setActionButtons(true);
            btnAudio.disabled = false;
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    loadStoryFromUrl();
})();
