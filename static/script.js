document.addEventListener('DOMContentLoaded', () => {
    const questionInput = document.getElementById('questionInput');
    const askBtn = document.getElementById('askBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultCard = document.getElementById('resultCard');
    const resultText = document.getElementById('resultText');
    const resultSource = document.getElementById('resultSource');
    const resultLatency = document.getElementById('resultLatency');
    const similarityScore = document.getElementById('similarityScore');
    const cacheList = document.getElementById('cacheList');
    const totalEntries = document.getElementById('totalEntries');
    const refreshCacheBtn = document.getElementById('refreshCacheBtn');
    const clearCacheBtn = document.getElementById('clearCacheBtn');

    let currentAnswer = '';
    let latestMetadata = null;
    let shouldRefreshCache = false;

    // Load cache on startup
    fetchCache();

    // Event Listeners
    askBtn.addEventListener('click', handleAsk);
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAsk();
    });
    refreshCacheBtn.addEventListener('click', fetchCache);
    clearCacheBtn.addEventListener('click', handleClearCache);

    async function handleAsk() {
        const question = questionInput.value.trim();
        if (!question) return;

        resetResultCard();

        loadingIndicator.classList.remove('hidden');
        askBtn.disabled = true;

        try {
            const response = await fetch('/ask/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });

            if (!response.ok) {
                throw new Error('Failed to get response from server');
            }

            await readStream(response);
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to get response');
        } finally {
            loadingIndicator.classList.add('hidden');
            askBtn.disabled = false;
        }
    }

    function resetResultCard() {
        currentAnswer = '';
        latestMetadata = null;
        shouldRefreshCache = false;
        resultText.textContent = '';
        resultLatency.textContent = '...';
        similarityScore.textContent = 'Similarity: --';
        resultSource.textContent = 'Waiting...';
        resultSource.className = 'source-badge';
        clearCitations();
        resultCard.classList.add('hidden');
    }

    async function readStream(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const event = JSON.parse(line);
                    handleStreamEvent(event);
                } catch (err) {
                    console.error('Failed to parse stream chunk', err, line);
                }
            }
        }

        if (buffer.trim()) {
            try {
                const event = JSON.parse(buffer);
                handleStreamEvent(event);
            } catch (err) {
                console.error('Failed to parse trailing chunk', err, buffer);
            }
        }
    }

    function handleStreamEvent(event) {
        switch (event.type) {
            case 'status':
                updateSource(event.source);
                shouldRefreshCache = event.source === 'CACHE_MISS';
                resultCard.classList.remove('hidden');
                break;
            case 'token':
                currentAnswer += event.text;
                renderAnswer(currentAnswer);
                resultCard.classList.remove('hidden');
                break;
            case 'metadata':
                latestMetadata = event;
                if (event.latency !== undefined) {
                    resultLatency.textContent = `${Number(event.latency).toFixed(4)}s`;
                }
                if (event.source) {
                    updateSource(event.source);
                    shouldRefreshCache = event.source === 'CACHE_MISS';
                }
                if (event.similarity) {
                    similarityScore.textContent = `Similarity: ${event.similarity}`;
                }
                if (event.answer && !currentAnswer) {
                    currentAnswer = event.answer;
                    renderAnswer(currentAnswer);
                }
                if (event.grounding_metadata) {
                    renderCitations(event.grounding_metadata);
                }
                resultCard.classList.remove('hidden');
                break;
            case 'error':
                alert(event.message || 'Generation failed');
                break;
            case 'done':
                if (shouldRefreshCache) {
                    fetchCache();
                }
                break;
            default:
                break;
        }
    }

    function renderAnswer(answerText) {
        resultText.innerHTML = formatMarkdown(answerText);
    }

    function updateSource(source) {
        if (!source) return;
        resultSource.textContent = source.replace('_', ' ');
        resultSource.className = 'source-badge ' + (source === 'CACHE_HIT' ? 'hit' : 'miss');
    }

    async function fetchCache() {
        try {
            const response = await fetch('/cache');
            const data = await response.json();
            renderCacheList(data.entries);
        } catch (error) {
            console.error('Error fetching cache:', error);
        }
    }

    function renderCacheList(entries) {
        totalEntries.textContent = entries.length;
        cacheList.innerHTML = '';

        entries.forEach(entry => {
            const div = document.createElement('div');
            div.className = 'cache-item';
            div.innerHTML = `
                <div class="cache-query">${entry.query}</div>
                <div class="cache-response">${entry.response}</div>
            `;
            // Click to populate search
            div.addEventListener('click', () => {
                questionInput.value = entry.query;
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
            cacheList.appendChild(div);
        });
    }

    async function handleClearCache() {
        if (!confirm('Are you sure you want to clear the entire cache?')) return;

        try {
            await fetch('/cache', { method: 'DELETE' });
            fetchCache();
        } catch (error) {
            console.error('Error clearing cache:', error);
        }
    }

    function renderCitations(metadata) {
        clearCitations();
        if (!metadata || !metadata.grounding_chunks || metadata.grounding_chunks.length === 0) return;

        const citationsDiv = document.createElement('div');
        citationsDiv.id = 'citations';
        citationsDiv.className = 'mt-4 p-3 bg-gray-50 rounded text-sm';
        citationsDiv.innerHTML = '<h4 class="font-semibold mb-2">Sources:</h4>';

        const list = document.createElement('ul');
        list.className = 'list-disc pl-5';
        metadata.grounding_chunks.forEach(chunk => {
            const li = document.createElement('li');
            li.innerHTML = `<a href="${chunk.uri}" target="_blank" class="text-blue-600 hover:underline">${chunk.title || chunk.uri}</a>`;
            list.appendChild(li);
        });
        citationsDiv.appendChild(list);
        resultText.parentNode.appendChild(citationsDiv);
    }

    function clearCitations() {
        const existingCitations = document.getElementById('citations');
        if (existingCitations) existingCitations.remove();
    }

    // Simple Markdown formatter for bold text
    function formatMarkdown(text) {
        return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }
});
