/**
 * StoryVerse AI — SSE client over fetch POST
 */
(function (global) {
    "use strict";

    function parseSseBlock(block) {
        let event = "message";
        let data = "";
        block.split("\n").forEach((line) => {
            if (line.startsWith("event:")) {
                event = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
                data += line.slice(5).trim();
            }
        });
        if (!data) return null;
        try {
            return { event, data: JSON.parse(data) };
        } catch (_) {
            return { event, data: { raw: data } };
        }
    }

    async function postSse(url, payload, handlers, csrfToken) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            let message = "Request failed.";
            try {
                const err = await response.json();
                message = err.error || message;
            } catch (_) {
                /* ignore */
            }
            throw new Error(message);
        }

        if (!response.body) {
            throw new Error("Streaming is not supported in this browser.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split("\n\n");
            buffer = parts.pop() || "";

            for (const part of parts) {
                const parsed = parseSseBlock(part.trim());
                if (!parsed) continue;

                const handler = handlers[parsed.event];
                if (handler) handler(parsed.data);
            }
        }

        const tail = buffer.trim();
        if (tail) {
            const parsed = parseSseBlock(tail);
            if (parsed && handlers[parsed.event]) {
                handlers[parsed.event](parsed.data);
            }
        }
    }

    global.StoryVerseSSE = { postSse };
})(window);
