/**
 * StoryVerse AI — Audiobook Studio
 * Waveform · Visualizer · Speech playback · Voice selection · MP3 download
 */

(function () {
    "use strict";

    if (!CanvasRenderingContext2D.prototype.roundRect) {
        CanvasRenderingContext2D.prototype.roundRect = function (x, y, w, h, r) {
            const radius = typeof r === "number" ? r : (r && r[0]) || 0;
            this.moveTo(x + radius, y);
            this.arcTo(x + w, y, x + w, y + h, radius);
            this.arcTo(x + w, y + h, x, y + h, radius);
            this.arcTo(x, y + h, x, y, radius);
            this.arcTo(x, y, x + w, y, radius);
            this.closePath();
        };
    }

    function initStudio() {
        const config = window.AUDIOBOOK_STUDIO;
        if (!config) return;

        /* DOM Elements */
        const storySelect = document.getElementById("story-select");
        const voiceGrid = document.getElementById("voice-grid");
        const genderFilterBtns = document.querySelectorAll(".ab-gender-filter[data-gender]");
        const regionFilterBtns = document.querySelectorAll(".ab-region-filter[data-region]");
        const musicGrid = document.getElementById("music-grid");
        const storyBanner = document.getElementById("story-banner");
        const bannerText = document.getElementById("banner-text");
        const musicHint = document.getElementById("music-hint");
        const voiceCountEl = document.getElementById("voice-count");
        const voiceEmptyEl = document.getElementById("voice-empty");
    const albumCover = document.getElementById("album-cover");
    const coverArt = document.getElementById("cover-art");
    const coverGlow = document.getElementById("cover-glow");
    const trackTitle = document.getElementById("track-title");
    const trackMeta = document.getElementById("track-meta");
    const trackTags = document.getElementById("track-tags");
    const storyPreview = document.getElementById("story-preview");
    const waveformCanvas = document.getElementById("waveform-canvas");
    const visualizerCanvas = document.getElementById("visualizer-canvas");
    const progressBar = document.getElementById("progress-bar");
    const progressFill = document.getElementById("progress-fill");
    const progressThumb = document.getElementById("progress-thumb");
    const timeCurrent = document.getElementById("time-current");
    const timeTotal = document.getElementById("time-total");
    const btnPlay = document.getElementById("btn-play");
    const playIcon = document.getElementById("play-icon");
    const btnSkipBack = document.getElementById("btn-skip-back");
    const btnSkipForward = document.getElementById("btn-skip-forward");
    const btnGenerate = document.getElementById("btn-generate");
    const btnGenerateLabel = document.getElementById("btn-generate-label");
    const btnDownload = document.getElementById("btn-download");
    const genOverlay = document.getElementById("gen-overlay");
    const genStatusLabel = document.getElementById("gen-status-label");
    const genBarFill = document.getElementById("gen-bar-fill");
    const genPercent = document.getElementById("gen-percent");
    const libraryEl = document.getElementById("audiobook-library");
    const libraryEmpty = document.getElementById("library-empty");
    const audioPlayer = document.getElementById("audio-player");
    const musicPlayer = document.getElementById("music-player");

    /* State */
    let stories = [];
    let libraryAudiobooks = [];
    let selectedStory = null;
    let selectedVoiceId = null;
    let selectedGender = "all";
    let selectedRegion = "all";
    let selectedMusicId = "auto";
    let audiobookId = null;
    let editingAudiobookId = null;
    let pollTimer = null;
    let isGenerating = false;
    let activePollId = null;
    let audioStreamUrl = null;
    let audioMusicStreamUrl = null;
    const MUSIC_VOLUME = 0.24;
    let hasRealAudio = false;
    let isGenerated = false;
    let isPlaying = false;
    let speechUtterance = null;
    let speechCharIndex = 0;
    let progressInterval = null;
    let visualizerFrame = null;
    let audioContext = null;
    let analyser = null;
    let audioSource = null;
    let mediaElementHooked = false;
    let estimatedDuration = 0;
    let elapsedSeconds = 0;
    let waveformData = [];

    const wfCtx = waveformCanvas ? waveformCanvas.getContext("2d") : null;
    const vizCtx = visualizerCanvas ? visualizerCanvas.getContext("2d") : null;

    if (!voiceGrid || !musicGrid || !storySelect) {
        console.error("Audiobook Studio: required elements missing from page.");
        return;
    }

    /* Utilities
       ================================================================== */

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s.toString().padStart(2, "0")}`;
    }

    function showToast(message, type) {
        const container = document.getElementById("toast-container");
        const id = "toast-" + Date.now();
        const bg = type === "success"
            ? "text-bg-success"
            : type === "info"
                ? "text-bg-warning"
                : "text-bg-danger";
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

    async function apiPost(url, payload) {
        const res = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": config.csrfToken,
            },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Request failed.");
        return data;
    }

    async function apiDelete(url) {
        const res = await fetch(url, {
            method: "DELETE",
            headers: { "X-CSRFToken": config.csrfToken },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Request failed.");
        return data;
    }

    function updateGenerateLabel() {
        if (btnGenerateLabel) {
            btnGenerateLabel.textContent = editingAudiobookId ? "Regenerate Audio" : "Generate Audio";
        }
    }

    function showGenOverlay() {
        if (genOverlay) genOverlay.classList.remove("d-none");
        updateGenProgress(0, "Starting conversion…");
    }

    function hideGenOverlay() {
        if (genOverlay) genOverlay.classList.add("d-none");
        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
        activePollId = null;
        isGenerating = false;
    }

    function updateGenProgress(percent, message) {
        const pct = Math.min(100, Math.max(0, percent || 0));
        if (genBarFill) genBarFill.style.width = `${pct}%`;
        if (genPercent) genPercent.textContent = `${pct}%`;
        if (genStatusLabel && message) genStatusLabel.textContent = message;
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

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function seededRandom(seed) {
        let s = seed;
        return function () {
            s = (s * 16807 + 0) % 2147483647;
            return (s - 1) / 2147483646;
        };
    }

    function hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = ((hash << 5) - hash) + str.charCodeAt(i);
            hash |= 0;
        }
        return Math.abs(hash);
    }

    /* Waveform
       ================================================================== */

    function generateWaveformData(seed, bars) {
        const rand = seededRandom(seed);
        const data = [];
        for (let i = 0; i < bars; i++) {
            const t = i / bars;
            const envelope = Math.sin(t * Math.PI) * 0.6 + 0.4;
            const noise = rand() * 0.5 + 0.2;
            const rhythm = Math.abs(Math.sin(t * 40 * Math.PI)) * 0.3;
            data.push(Math.min(1, (noise + rhythm) * envelope));
        }
        return data;
    }

    function drawWaveform(progress) {
        if (!waveformCanvas || !wfCtx || !waveformData.length) return;
        const dpr = window.devicePixelRatio || 1;
        const rect = waveformCanvas.getBoundingClientRect();
        waveformCanvas.width = rect.width * dpr;
        waveformCanvas.height = rect.height * dpr;
        wfCtx.scale(dpr, dpr);

        const w = rect.width;
        const h = rect.height;
        const barCount = waveformData.length;
        const barWidth = w / barCount;
        const gap = 2;
        const progressIndex = Math.floor(progress * barCount);

        wfCtx.clearRect(0, 0, w, h);

        for (let i = 0; i < barCount; i++) {
            const barH = waveformData[i] * (h - 16);
            const x = i * barWidth + gap / 2;
            const y = (h - barH) / 2;
            const bw = barWidth - gap;

            if (i <= progressIndex) {
                const grad = wfCtx.createLinearGradient(x, y, x, y + barH);
                grad.addColorStop(0, "#1ed760");
                grad.addColorStop(1, "#00d4ff");
                wfCtx.fillStyle = grad;
            } else {
                wfCtx.fillStyle = "rgba(255, 255, 255, 0.12)";
            }

            wfCtx.beginPath();
            wfCtx.roundRect(x, y, bw, barH, 2);
            wfCtx.fill();
        }

        wfCtx.setTransform(1, 0, 0, 1, 0, 0);
    }

    /* Visualizer
       ================================================================== */

    function startVisualizer() {
        if (!visualizerCanvas || !vizCtx) return;
        const rect = visualizerCanvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        visualizerCanvas.width = rect.width * dpr;
        visualizerCanvas.height = rect.height * dpr;

        function draw() {
            vizCtx.setTransform(1, 0, 0, 1, 0, 0);
            vizCtx.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);
            vizCtx.scale(dpr, dpr);

            const w = rect.width;
            const h = rect.height;
            const bars = 48;
            const barW = w / bars - 2;

            let frequencyData;
            if (analyser && isPlaying && !audioPlayer.paused) {
                frequencyData = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(frequencyData);
            }

            for (let i = 0; i < bars; i++) {
                let value;
                if (frequencyData) {
                    const idx = Math.floor(i * frequencyData.length / bars);
                    value = frequencyData[idx] / 255;
                } else {
                    value = 0.15 + Math.random() * 0.85 * (isPlaying ? 1 : 0.1);
                }

                const barH = value * (h - 8);
                const x = i * (barW + 2) + 1;
                const y = h - barH;

                const grad = vizCtx.createLinearGradient(x, y, x, h);
                grad.addColorStop(0, "#1ed760");
                grad.addColorStop(0.5, "#00d4ff");
                grad.addColorStop(1, "#a855f7");

                vizCtx.fillStyle = grad;
                vizCtx.beginPath();
                vizCtx.roundRect(x, y, barW, barH, 2);
                vizCtx.fill();
            }

            vizCtx.setTransform(1, 0, 0, 1, 0, 0);
            visualizerFrame = requestAnimationFrame(draw);
        }

        draw();
    }

    function stopVisualizer() {
        if (visualizerFrame) {
            cancelAnimationFrame(visualizerFrame);
            visualizerFrame = null;
        }
        drawIdleVisualizer();
    }

    function drawIdleVisualizer() {
        if (!visualizerCanvas || !vizCtx) return;
        const dpr = window.devicePixelRatio || 1;
        const rect = visualizerCanvas.getBoundingClientRect();
        visualizerCanvas.width = rect.width * dpr;
        visualizerCanvas.height = rect.height * dpr;
        vizCtx.setTransform(1, 0, 0, 1, 0, 0);
        vizCtx.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);
        vizCtx.scale(dpr, dpr);

        const w = rect.width;
        const h = rect.height;
        const bars = 48;
        const barW = w / bars - 2;

        for (let i = 0; i < bars; i++) {
            const barH = 4 + Math.sin(i * 0.3) * 3;
            const x = i * (barW + 2) + 1;
            vizCtx.fillStyle = "rgba(255, 255, 255, 0.08)";
            vizCtx.beginPath();
            vizCtx.roundRect(x, h - barH - 4, barW, barH, 2);
            vizCtx.fill();
        }
        vizCtx.setTransform(1, 0, 0, 1, 0, 0);
    }

    /* Audio Context
       ================================================================== */

    function setupAudioContext() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            analyser.connect(audioContext.destination);
        }
    }

    function connectAudioElement() {
        if (!audioPlayer.src || mediaElementHooked) return;
        try {
            setupAudioContext();
            audioSource = audioContext.createMediaElementSource(audioPlayer);
            audioSource.connect(analyser);
            mediaElementHooked = true;
        } catch (_) {
            audioSource = null;
        }
    }

    function waitForAudioReady() {
        if (audioPlayer.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
            return Promise.resolve();
        }
        return new Promise((resolve, reject) => {
            const onReady = () => {
                cleanup();
                resolve();
            };
            const onError = () => {
                cleanup();
                reject(new Error("Could not load audio file."));
            };
            const cleanup = () => {
                audioPlayer.removeEventListener("canplay", onReady);
                audioPlayer.removeEventListener("error", onError);
            };
            audioPlayer.addEventListener("canplay", onReady, { once: true });
            audioPlayer.addEventListener("error", onError, { once: true });
        });
    }

    async function resumeAudioContext() {
        setupAudioContext();
        if (audioContext && audioContext.state === "suspended") {
            await audioContext.resume();
        }
    }

    /* Progress
       ================================================================== */

    function updateProgress(seconds) {
        elapsedSeconds = seconds;
        const progress = estimatedDuration > 0 ? Math.min(seconds / estimatedDuration, 1) : 0;
        progressFill.style.width = `${progress * 100}%`;
        progressThumb.style.left = `${progress * 100}%`;
        timeCurrent.textContent = formatTime(seconds);
        drawWaveform(progress);
    }

    function startProgressTimer() {
        clearInterval(progressInterval);
        const startTime = Date.now() - elapsedSeconds * 1000;
        progressInterval = setInterval(() => {
            const elapsed = (Date.now() - startTime) / 1000;
            if (elapsed >= estimatedDuration) {
                updateProgress(estimatedDuration);
                stopPlayback();
            } else {
                updateProgress(elapsed);
            }
        }, 200);
    }

    function stopProgressTimer() {
        clearInterval(progressInterval);
    }

    /* Speech Synthesis Playback
       ================================================================== */

    function getSpeechVoice(voiceId) {
        const voices = speechSynthesis.getVoices();
        const isMale = voiceId && ["atlas", "marcus", "ethan", "james"].includes(voiceId);
        const preferred = voices.filter((v) => v.lang.startsWith("en"));
        if (!preferred.length) return voices[0] || null;

        const genderMatch = preferred.filter((v) => {
            const name = v.name.toLowerCase();
            if (isMale) return name.includes("male") || name.includes("david") || name.includes("james") || name.includes("daniel");
            return name.includes("female") || name.includes("samantha") || name.includes("karen") || name.includes("victoria");
        });
        return genderMatch[0] || preferred[0];
    }

    function speakFromIndex(text, charIndex) {
        const remaining = text.slice(charIndex);
        if (!remaining) return;

        speechUtterance = new SpeechSynthesisUtterance(remaining);
        speechUtterance.rate = 0.95;
        speechUtterance.pitch = 1;
        const voice = getSpeechVoice(selectedVoiceId);
        if (voice) speechUtterance.voice = voice;

        speechUtterance.onboundary = (e) => {
            if (e.charIndex !== undefined) {
                speechCharIndex = charIndex + e.charIndex;
            }
        };

        speechUtterance.onend = () => {
            if (isPlaying) stopPlayback();
        };

        speechUtterance.onerror = () => {
            stopPlayback();
        };

        speechSynthesis.speak(speechUtterance);
    }

    /* Playback Controls
       ================================================================== */

    function setPlayingState(playing) {
        isPlaying = playing;
        playIcon.className = playing ? "bi bi-pause-fill" : "bi bi-play-fill";
        btnPlay.classList.toggle("is-playing", playing);
        albumCover.classList.toggle("is-playing", playing);
        coverGlow.classList.toggle("is-active", playing);

        if (playing) {
            startVisualizer();
            if (!audioStreamUrl) {
                startProgressTimer();
            }
        } else {
            stopVisualizer();
            stopProgressTimer();
        }
    }

    async function startPlayback() {
        if (!selectedStory || !isGenerated) return;

        if (audioStreamUrl) {
            try {
                await resumeAudioContext();

                if (!audioPlayer.src || !audioPlayer.src.includes(String(audiobookId))) {
                    audioPlayer.src = audioStreamUrl;
                    audioPlayer.load();
                }

                if (audioMusicStreamUrl) {
                    if (!musicPlayer.src || !musicPlayer.src.includes(String(audiobookId))) {
                        musicPlayer.src = audioMusicStreamUrl;
                        musicPlayer.volume = MUSIC_VOLUME;
                        musicPlayer.load();
                    }
                } else {
                    musicPlayer.removeAttribute("src");
                }

                await waitForAudioReady();
                connectAudioElement();
                const playTasks = [audioPlayer.play()];
                if (audioMusicStreamUrl && musicPlayer.src) {
                    musicPlayer.currentTime = audioPlayer.currentTime || 0;
                    playTasks.push(musicPlayer.play());
                }
                await Promise.all(playTasks);
                setPlayingState(true);
            } catch (err) {
                showToast(err.message || "Unable to play audio. Try generating again.", "error");
                setPlayingState(false);
            }
            return;
        }

        speechSynthesis.cancel();
        speakFromIndex(selectedStory.content, speechCharIndex);
        setPlayingState(true);
    }

    function pausePlayback() {
        if (audioPlayer.src) {
            audioPlayer.pause();
            if (musicPlayer.src) {
                musicPlayer.pause();
            }
        } else {
            speechSynthesis.cancel();
        }
        setPlayingState(false);
    }

    function stopPlayback() {
        if (audioPlayer.src) {
            audioPlayer.pause();
            audioPlayer.currentTime = 0;
        }
        if (musicPlayer.src) {
            musicPlayer.pause();
            musicPlayer.currentTime = 0;
        } else {
            speechSynthesis.cancel();
        }
        speechCharIndex = 0;
        elapsedSeconds = 0;
        updateProgress(0);
        setPlayingState(false);
    }

    function togglePlayback() {
        if (isPlaying) {
            pausePlayback();
        } else {
            startPlayback();
        }
    }

    /* UI Updates
       ================================================================== */

    function updateCover(colors) {
        const [from, to] = colors || ["#1db954", "#191414"];
        coverArt.style.background = `linear-gradient(135deg, ${from} 0%, ${to} 100%)`;
        coverGlow.style.background = `radial-gradient(circle, ${from}40 0%, transparent 70%)`;
    }

    function selectStory(story) {
        selectedStory = story;
        isGenerated = false;
        audiobookId = null;
        audioStreamUrl = null;
        audioMusicStreamUrl = null;
        hasRealAudio = false;
        speechCharIndex = 0;
        elapsedSeconds = 0;

        stopPlayback();
        audioPlayer.removeAttribute("src");
        audioPlayer.load();
        musicPlayer.removeAttribute("src");
        musicPlayer.load();

        trackTitle.textContent = story.title;
        trackMeta.textContent = `${story.genre_label} · ${story.word_count} words · ~${formatTime(story.duration_estimate)}`;
        trackTags.innerHTML = `
            <span class="ab-tag">${story.genre_label}</span>
            <span class="ab-tag">${story.word_count} words</span>
        `;

        const preview = story.content.slice(0, 400) + (story.content.length > 400 ? "…" : "");
        storyPreview.innerHTML = `<p>${preview.replace(/\n/g, "<br>")}</p>`;

        updateCover([story.cover.color_from, story.cover.color_to]);

        estimatedDuration = story.duration_estimate;
        timeTotal.textContent = formatTime(estimatedDuration);
        updateProgress(0);

        waveformData = generateWaveformData(hashCode(story.content), 120);
        drawWaveform(0);

        applyStoryRecommendations(story);

        btnGenerate.disabled = !selectedVoiceId;
        btnPlay.disabled = true;
        btnDownload.disabled = true;
        btnSkipBack.disabled = true;
        btnSkipForward.disabled = true;
    }

    function onAudiobookGenerated(data, message) {
        isGenerated = true;
        audiobookId = data.audiobook_id;
        audioStreamUrl = data.stream_url || null;
        audioMusicStreamUrl = data.music_stream_url || null;
        hasRealAudio = data.audio_source === "elevenlabs";
        estimatedDuration = data.duration_seconds;
        timeTotal.textContent = formatTime(estimatedDuration);

        const sourceLabel = hasRealAudio ? "ElevenLabs" : "Demo audio";
        const musicLabel = data.music_label || "No Music";
        const voiceName = data.voice?.name || data.voice_name || "Voice";
        const genrePart = data.genre_label ? `${data.genre_label} · ` : "";
        trackMeta.textContent = `${genrePart}${voiceName} · ${musicLabel}`;
        trackTags.innerHTML = `
            ${data.genre_label ? `<span class="ab-tag">${data.genre_label}</span>` : ""}
            <span class="ab-tag">${voiceName}</span>
            <span class="ab-tag">${musicLabel}</span>
            <span class="ab-tag">${sourceLabel}</span>
        `;

        btnPlay.disabled = false;
        btnDownload.disabled = false;
        btnSkipBack.disabled = false;
        btnSkipForward.disabled = false;

        loadAudio();
        const toastType = data.audio_source === "demo" ? "info" : "success";
        showToast(message || "Audiobook ready! Press play to preview.", toastType);
        loadLibrary();
    }

    async function pollGenerationStatus(id) {
        if (activePollId && activePollId !== id) return;
        activePollId = id;
        isGenerating = true;
        try {
            const url = config.urls.status.replace("{id}", id);
            const res = await fetch(url);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Status check failed.");

            const ab = data.audiobook;
            updateGenProgress(ab.progress, ab.status_message || "Converting…");
            syncLibraryItem(ab);

            if (data.done) {
                hideGenOverlay();
                btnGenerate.classList.remove("is-loading");
                btnGenerate.disabled = !selectedStory || !selectedVoiceId;
                if (ab.status === "failed") {
                    showToast(ab.error_message || "Audio conversion failed.", "error");
                } else {
                    onAudiobookGenerated(ab, ab.status_message);
                }
                editingAudiobookId = null;
                updateGenerateLabel();
                await loadLibrary();
                return;
            }
            pollTimer = setTimeout(() => pollGenerationStatus(id), 600);
        } catch (err) {
            hideGenOverlay();
            showToast(err.message, "error");
            btnGenerate.classList.remove("is-loading");
            btnGenerate.disabled = !selectedStory || !selectedVoiceId;
            loadLibrary();
        }
    }

    function syncLibraryItem(ab) {
        const idx = libraryAudiobooks.findIndex((item) => item.audiobook_id === ab.audiobook_id);
        if (idx >= 0) libraryAudiobooks[idx] = ab;
        renderLibrary();
    }

    function renderLibrary() {
        if (!libraryEl) return;

        if (!libraryAudiobooks.length) {
            libraryEl.innerHTML = "";
            if (libraryEmpty) libraryEmpty.classList.remove("d-none");
            return;
        }

        if (libraryEmpty) libraryEmpty.classList.add("d-none");

        libraryEl.innerHTML = libraryAudiobooks.map((ab) => {
            const isProcessing = ab.status === "processing";
            const isFailed = ab.status === "failed";
            const statusClass = isProcessing ? "ab-lib-status--processing"
                : isFailed ? "ab-lib-status--failed" : "ab-lib-status--ready";
            const statusLabel = isProcessing ? "Converting…"
                : isFailed ? "Failed" : "Ready";

            const actions = isProcessing
                ? `<div class="ab-lib-progress"><div class="ab-lib-progress-fill" style="width:${ab.progress || 0}%"></div></div>
                   <span class="ab-lib-progress-text">${escapeHtml(ab.status_message || "Converting…")} · ${ab.progress || 0}%</span>`
                : `<div class="ab-lib-actions">
                    <button type="button" class="ab-lib-btn ab-lib-btn-play" data-action="play" data-id="${ab.audiobook_id}" ${isFailed ? "disabled" : ""}>
                        <i class="bi bi-play-fill"></i> Play
                    </button>
                    <button type="button" class="ab-lib-btn ab-lib-btn-edit" data-action="modify" data-id="${ab.audiobook_id}">
                        <i class="bi bi-pencil"></i> Modify
                    </button>
                    <button type="button" class="ab-lib-btn ab-lib-btn-delete" data-action="delete" data-id="${ab.audiobook_id}">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                   </div>`;

            return `
                <article class="ab-lib-card ${isProcessing ? "ab-lib-card--processing" : ""}" data-id="${ab.audiobook_id}">
                    <div class="ab-lib-main">
                        <h4 class="ab-lib-title">${escapeHtml(ab.title)}</h4>
                        <p class="ab-lib-meta">
                            ${escapeHtml(ab.voice_name || ab.voice?.name || "Voice")}
                            · ${escapeHtml(ab.music_label || "No Music")}
                            · ${formatTime(ab.duration_seconds || 0)}
                        </p>
                        <p class="ab-lib-date">${formatDate(ab.created_at)}</p>
                    </div>
                    <div class="ab-lib-side">
                        <span class="ab-lib-status ${statusClass}">${statusLabel}</span>
                        ${actions}
                    </div>
                </article>`;
        }).join("");
    }

    async function loadLibrary() {
        if (!config.urls.audiobooks) return;
        try {
            const res = await fetch(config.urls.audiobooks);
            const data = await res.json();
            libraryAudiobooks = data.audiobooks || [];
            renderLibrary();

            const processing = libraryAudiobooks.find((ab) => ab.status === "processing");
            if (processing && !isGenerating && genOverlay && genOverlay.classList.contains("d-none")) {
                showGenOverlay();
                pollGenerationStatus(processing.audiobook_id);
            }
        } catch (_) {
            /* library is optional UI */
        }
    }

    async function deleteAudiobookItem(id) {
        if (!confirm("Delete this audiobook? This cannot be undone.")) return;
        try {
            const url = config.urls.delete.replace("{id}", id);
            await apiDelete(url);
            if (audiobookId === id) {
                stopPlayback();
                audiobookId = null;
                isGenerated = false;
                btnPlay.disabled = true;
                btnDownload.disabled = true;
            }
            if (editingAudiobookId === id) {
                editingAudiobookId = null;
                updateGenerateLabel();
            }
            showToast("Audiobook deleted.", "success");
            await loadLibrary();
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    function loadAudiobookForModify(ab) {
        editingAudiobookId = ab.audiobook_id;
        updateGenerateLabel();

        const story = stories.find((s) => s.id === ab.story_id);
        if (story) {
            storySelect.value = String(story.id);
            selectStory(story);
        }

        if (ab.voice_id) selectVoice(ab.voice_id);

        const musicId = ab.music_style || "auto";
        const hasAuto = musicGrid.querySelector('[data-music-id="auto"]');
        const hasStyle = musicGrid.querySelector(`[data-music-id="${musicId}"]`);
        selectMusic(hasStyle ? musicId : (hasAuto ? "auto" : musicId));

        document.getElementById("ab-studio")?.scrollIntoView({ behavior: "smooth" });
        showToast("Adjust voice or music, then click Regenerate Audio.", "success");
    }

    function loadAudiobookForPlay(ab) {
        if (ab.status !== "ready" || !ab.stream_url) {
            showToast("Audio is not ready to play yet.", "error");
            return;
        }
        const story = stories.find((s) => s.id === ab.story_id);
        if (story) {
            storySelect.value = String(story.id);
            selectStory(story);
        }
        onAudiobookGenerated(ab, "Loaded from your library.");
    }

    function loadAudio() {
        if (!audiobookId || !audioStreamUrl) return;
        audioPlayer.src = audioStreamUrl;
        audioPlayer.load();
        if (audioMusicStreamUrl) {
            musicPlayer.src = audioMusicStreamUrl;
            musicPlayer.volume = MUSIC_VOLUME;
            musicPlayer.load();
        } else {
            musicPlayer.removeAttribute("src");
        }
    }

    /* Voice, Region & Music
       ================================================================== */

    function resolveStoryMusic(story) {
        if (!story) return "none";
        if (story.recommended_music) return story.recommended_music;
        const genreMap = config.genreDefaultMusic && config.genreDefaultMusic[story.genre];
        if (genreMap) {
            const key = story.language === "hi" ? "hi" : "en";
            return genreMap[key] || genreMap.en || "none";
        }
        return story.language === "hi" ? "indian_classical" : "none";
    }

    function musicLabelForId(musicId) {
        const card = musicGrid.querySelector(`[data-music-id="${musicId}"]`);
        if (!card) return musicId;
        const name = card.querySelector(".ab-music-name");
        return name ? name.textContent.trim() : musicId;
    }

    function highlightRecommendedMusic(musicId) {
        musicGrid.querySelectorAll(".ab-music-card").forEach((card) => {
            card.classList.toggle("is-recommended", card.dataset.musicId === musicId);
        });
        if (musicHint) {
            musicHint.textContent = `Recommended for this story: ${musicLabelForId(musicId)}`;
        }
    }

    function highlightRecommendedVoices(voiceIds) {
        voiceGrid.querySelectorAll(".ab-voice-card").forEach((card) => {
            card.classList.toggle("is-recommended", voiceIds.includes(card.dataset.voiceId));
        });
    }

    function applyStoryRecommendations(story) {
        const recMusic = resolveStoryMusic(story);
        selectedMusicId = "auto";
        musicGrid.querySelectorAll(".ab-music-card").forEach((card) => {
            card.classList.toggle("selected", card.dataset.musicId === "auto");
        });
        highlightRecommendedMusic(recMusic);

        if (story.language === "hi") {
            selectedRegion = "indian";
            regionFilterBtns.forEach((btn) => {
                btn.classList.toggle("active", btn.dataset.region === "indian");
            });
            applyVoiceFilters();
        } else {
            filterRegions("all");
        }

        highlightRecommendedVoices(story.recommended_voices || []);

        const recVoice = (story.recommended_voices || [])[0];
        let recVoiceName = recVoice;
        if (recVoice) {
            const card = voiceGrid.querySelector(`[data-voice-id="${recVoice}"]:not(.hidden)`);
            if (card) {
                selectVoice(recVoice);
                const nameEl = card.querySelector(".ab-voice-name");
                recVoiceName = nameEl ? nameEl.textContent.replace(" EL", "").trim() : recVoice;
            }
        }

        if (storyBanner && bannerText) {
            storyBanner.classList.remove("d-none");
            const lang = story.language_label || story.language;
            bannerText.textContent =
                `${story.genre_label} · ${lang} — music: ${musicLabelForId(recMusic)}` +
                (recVoiceName ? ` · suggested voice: ${recVoiceName}` : "");
        }

        trackTags.innerHTML = `
            <span class="ab-tag">${story.genre_label}</span>
            <span class="ab-tag">${story.language_label || story.language}</span>
            <span class="ab-tag ab-tag-rec"><i class="bi bi-music-note"></i> ${musicLabelForId(recMusic)}</span>
        `;
    }

    function applyVoiceFilters() {
        let visible = 0;
        let selectedStillVisible = false;

        voiceGrid.querySelectorAll(".ab-voice-card").forEach((card) => {
            const genderOk = selectedGender === "all" || card.dataset.gender === selectedGender;
            const regionOk = selectedRegion === "all" || card.dataset.region === selectedRegion;
            const show = genderOk && regionOk;
            card.classList.toggle("hidden", !show);
            if (show) {
                visible += 1;
                if (card.dataset.voiceId === selectedVoiceId) {
                    selectedStillVisible = true;
                }
            }
        });

        if (!selectedStillVisible) {
            selectedVoiceId = null;
            voiceGrid.querySelectorAll(".ab-voice-card").forEach((card) => {
                card.classList.remove("selected");
            });
            const firstVisible = voiceGrid.querySelector(".ab-voice-card:not(.hidden)");
            if (firstVisible) {
                selectVoice(firstVisible.dataset.voiceId);
            } else {
                btnGenerate.disabled = !selectedStory || !selectedVoiceId;
            }
        }

        if (voiceCountEl) voiceCountEl.textContent = `(${visible})`;
        if (voiceEmptyEl) voiceEmptyEl.classList.toggle("d-none", visible > 0);
    }

    function filterVoices(gender) {
        selectedGender = gender;
        genderFilterBtns.forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.gender === gender);
        });
        applyVoiceFilters();
    }

    function filterRegions(region) {
        selectedRegion = region;
        regionFilterBtns.forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.region === region);
        });
        applyVoiceFilters();
    }

    function selectMusic(musicId) {
        selectedMusicId = musicId;
        musicGrid.querySelectorAll(".ab-music-card").forEach((card) => {
            card.classList.toggle("selected", card.dataset.musicId === musicId);
        });
    }

    function selectVoice(voiceId) {
        selectedVoiceId = voiceId;
        voiceGrid.querySelectorAll(".ab-voice-card").forEach((card) => {
            card.classList.toggle("selected", card.dataset.voiceId === voiceId);
        });
        btnGenerate.disabled = !selectedStory || !selectedVoiceId;
    }

    /* Load Stories
       ================================================================== */

    async function loadStories() {
        try {
            const res = await fetch(config.urls.stories);
            const data = await res.json();
            stories = data.stories || [];

            storySelect.innerHTML = '<option value="">Choose a story…</option>';
            stories.forEach((s) => {
                storySelect.insertAdjacentHTML("beforeend",
                    `<option value="${s.id}">${s.title}</option>`);
            });

            if (config.preselectedStoryId) {
                const preselectedId = Number(config.preselectedStoryId);
                storySelect.value = String(preselectedId);
                const story = stories.find((s) => s.id === preselectedId);
                if (story) selectStory(story);
            }
        } catch (_) {
            showToast("Failed to load stories.", "error");
        }
    }

    /* Event Listeners
       ================================================================== */

    storySelect.addEventListener("change", () => {
        editingAudiobookId = null;
        updateGenerateLabel();
        const story = stories.find((s) => s.id === parseInt(storySelect.value, 10));
        if (story) selectStory(story);
    });

    genderFilterBtns.forEach((btn) => {
        btn.addEventListener("click", () => filterVoices(btn.dataset.gender));
    });

    regionFilterBtns.forEach((btn) => {
        btn.addEventListener("click", () => filterRegions(btn.dataset.region));
    });

    musicGrid.addEventListener("click", (e) => {
        const card = e.target.closest(".ab-music-card");
        if (!card) return;
        e.preventDefault();
        selectMusic(card.dataset.musicId);
    });

    voiceGrid.addEventListener("click", (e) => {
        const card = e.target.closest(".ab-voice-card");
        if (!card || card.classList.contains("hidden")) return;
        e.preventDefault();
        selectVoice(card.dataset.voiceId);
    });

    btnPlay.addEventListener("click", togglePlayback);

    btnSkipBack.addEventListener("click", () => {
        speechCharIndex = 0;
        elapsedSeconds = 0;
        if (audioPlayer.src) audioPlayer.currentTime = 0;
        if (musicPlayer.src) musicPlayer.currentTime = 0;
        else if (isPlaying) {
            speechSynthesis.cancel();
            speakFromIndex(selectedStory.content, 0);
        }
        updateProgress(0);
    });

    btnSkipForward.addEventListener("click", () => {
        const skip = Math.min(elapsedSeconds + 15, estimatedDuration);
        elapsedSeconds = skip;
        if (audioPlayer.src) {
            audioPlayer.currentTime = skip;
        }
        if (musicPlayer.src) {
            musicPlayer.currentTime = skip;
        } else {
            speechCharIndex = Math.floor((skip / estimatedDuration) * selectedStory.content.length);
            if (isPlaying) {
                speechSynthesis.cancel();
                speakFromIndex(selectedStory.content, speechCharIndex);
            }
        }
        updateProgress(skip);
    });

    progressBar.addEventListener("click", (e) => {
        if (!selectedStory || !isGenerated) return;
        const rect = progressBar.getBoundingClientRect();
        const ratio = (e.clientX - rect.left) / rect.width;
        const seekTo = ratio * estimatedDuration;
        elapsedSeconds = seekTo;
        if (audioPlayer.src) {
            audioPlayer.currentTime = seekTo;
        }
        if (musicPlayer.src) {
            musicPlayer.currentTime = seekTo;
        } else {
            speechCharIndex = Math.floor(ratio * selectedStory.content.length);
            if (isPlaying) {
                speechSynthesis.cancel();
                speakFromIndex(selectedStory.content, speechCharIndex);
            }
        }
        updateProgress(seekTo);
    });

    if (waveformCanvas) {
        waveformCanvas.addEventListener("click", (e) => {
            progressBar.dispatchEvent(new MouseEvent("click", { clientX: e.clientX }));
        });
    }

    btnGenerate.addEventListener("click", async () => {
        if (!selectedStory || !selectedVoiceId || isGenerating) return;

        isGenerating = true;
        btnGenerate.classList.add("is-loading");
        btnGenerate.disabled = true;
        showGenOverlay();

        try {
            const payload = {
                story_id: selectedStory.id,
                voice_id: selectedVoiceId,
                music_style: selectedMusicId,
            };
            if (editingAudiobookId) payload.audiobook_id = editingAudiobookId;

            const data = await apiPost(config.urls.generate, payload);
            await loadLibrary();
            pollGenerationStatus(data.audiobook_id);
        } catch (err) {
            hideGenOverlay();
            showToast(err.message, "error");
            btnGenerate.classList.remove("is-loading");
            btnGenerate.disabled = !selectedStory || !selectedVoiceId;
            isGenerating = false;
        }
    });

    if (libraryEl) {
        libraryEl.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-action]");
            if (!btn) return;
            const id = parseInt(btn.dataset.id, 10);
            const ab = libraryAudiobooks.find((item) => item.audiobook_id === id);
            if (!ab) return;

            if (btn.dataset.action === "play") loadAudiobookForPlay(ab);
            else if (btn.dataset.action === "modify") loadAudiobookForModify(ab);
            else if (btn.dataset.action === "delete") deleteAudiobookItem(id);
        });
    }

    btnDownload.addEventListener("click", () => {
        if (!audiobookId) {
            showToast("Generate audio first before downloading.", "error");
            return;
        }
        const url = config.urls.download.replace("{id}", audiobookId);
        const a = document.createElement("a");
        a.href = url;
        a.download = "";
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("Download started!", "success");
    });

    audioPlayer.addEventListener("loadedmetadata", () => {
        if (audioPlayer.duration && isFinite(audioPlayer.duration)) {
            estimatedDuration = audioPlayer.duration;
            timeTotal.textContent = formatTime(estimatedDuration);
        }
    });

    audioPlayer.addEventListener("timeupdate", () => {
        if (audioPlayer.src) {
            updateProgress(audioPlayer.currentTime);
        }
    });

    audioPlayer.addEventListener("pause", () => {
        if (musicPlayer.src && !audioPlayer.ended) {
            musicPlayer.pause();
        }
    });

    audioPlayer.addEventListener("play", () => {
        if (musicPlayer.src && isPlaying) {
            musicPlayer.currentTime = audioPlayer.currentTime;
            musicPlayer.play().catch(() => {});
        }
    });

    audioPlayer.addEventListener("error", () => {
        if (!audioPlayer.src) return;
        showToast("Audio failed to load. Please generate again.", "error");
        setPlayingState(false);
    });

    audioPlayer.addEventListener("ended", () => stopPlayback());

    window.addEventListener("resize", () => {
        if (waveformData.length) drawWaveform(elapsedSeconds / estimatedDuration || 0);
        drawIdleVisualizer();
    });

    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = () => {};
    }

    /* Init
       ================================================================== */

    drawIdleVisualizer();
    loadStories();
    loadLibrary();
    updateGenerateLabel();

    if (voiceGrid.querySelector(".ab-voice-card")) {
        applyVoiceFilters();
        const firstVisible = voiceGrid.querySelector(".ab-voice-card:not(.hidden)");
        if (firstVisible) selectVoice(firstVisible.dataset.voiceId);
    }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initStudio);
    } else {
        initStudio();
    }
})();
