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

        // UI State: Loading
        loadingIndicator.classList.remove('hidden');
        resultCard.classList.add('hidden');
        askBtn.disabled = true;

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });

            const data = await response.json();

            // Update UI with Result
            displayResult(data);

            // Refresh cache list if it was a miss (new item added)
            if (data.source === 'CACHE_MISS') {
                fetchCache();
            }

        } catch (error) {
            console.error('Error:', error);
            alert('Failed to get response');
        } finally {
            loadingIndicator.classList.add('hidden');
            askBtn.disabled = false;
        }
    }

    function displayResult(data) {
        resultText.innerHTML = formatMarkdown(data.answer);
        resultLatency.textContent = `${data.latency.toFixed(4)}s`;

        resultSource.textContent = data.source.replace('_', ' ');
        resultSource.className = 'source-badge ' + (data.source === 'CACHE_HIT' ? 'hit' : 'miss');

        similarityScore.textContent = `Similarity: ${data.similarity}`;

        resultCard.classList.remove('hidden');
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

    // Simple Markdown formatter for bold text
    function formatMarkdown(text) {
        return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }
});
