const sidebar = document.querySelector('.sidebar');
const btnCollapse = document.getElementById('btn-collapse');
const btnExpand = document.getElementById('btn-expand');

if (localStorage.getItem('sidebar-collapsed') === '1') {
    sidebar.classList.add('collapsed');
}

function setSidebarCollapsed(collapsed) {
    sidebar.classList.toggle('collapsed', collapsed);
    localStorage.setItem('sidebar-collapsed', collapsed ? '1' : '0');
}

btnCollapse.addEventListener('click', () => setSidebarCollapsed(true));
btnExpand.addEventListener('click', () => setSidebarCollapsed(false));

const btnTheme = document.getElementById('btn-theme');

function prefersDark() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function currentTheme() {
    return document.documentElement.getAttribute('data-theme') || (prefersDark() ? 'dark' : 'light');
}

btnTheme.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
});

const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        navItems.forEach(t => t.classList.remove('active'));
        views.forEach(v => v.classList.add('hidden'));
        item.classList.add('active');
        document.getElementById('tab-' + item.dataset.tab).classList.remove('hidden');
        if (item.dataset.tab === 'browse') loadEntries();
    });
});

async function checkHealth() {
    const el = document.getElementById('health-status');
    const text = el.querySelector('.health-text');
    try {
        const res = await fetch('/api/health');
        const data = await res.json();
        if (data.ollama_ready) {
            text.textContent = 'Ollama connected';
            el.className = 'health ok';
        } else {
            text.textContent = 'Ollama not ready';
            el.className = 'health error';
        }
    } catch {
        text.textContent = 'Backend unreachable';
        el.className = 'health error';
    }
}
checkHealth();

function streamSSE(url, body, onText, onEvent) {
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        function read() {
            return reader.read().then(({ done, value }) => {
                if (done) return;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = JSON.parse(line.slice(6));
                    if (data.text) onText(data.text);
                    onEvent(data);
                    if (data.done) return;
                }
                return read();
            });
        }
        return read();
    });
}

let sessionId = 'session_' + Date.now();
let polishedText = '';
let editing = false;

const btnStart = document.getElementById('btn-start');
const btnReply = document.getElementById('btn-reply');
const btnDone = document.getElementById('btn-done');
const btnEditToggle = document.getElementById('btn-edit-toggle');
const btnSave = document.getElementById('btn-save');
const btnNew = document.getElementById('btn-new');

btnStart.addEventListener('click', () => {
    const rawDump = document.getElementById('raw-dump').value.trim();
    if (!rawDump) return;

    document.getElementById('dump-input').classList.add('hidden');
    document.getElementById('dump-chat').classList.remove('hidden');

    addChatMsg('user', rawDump);
    const assistantEl = addChatMsg('assistant', '', true);

    btnStart.disabled = true;
    streamSSE(
        '/api/braindump/start',
        { raw_dump: rawDump, session_id: sessionId },
        text => {
            assistantEl.textContent += text;
            scrollChat();
        },
        data => {
            if (data.done) assistantEl.classList.remove('streaming');
        }
    );
});

btnReply.addEventListener('click', sendReply);
document.getElementById('chat-reply').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendReply();
    }
});

function sendReply() {
    const input = document.getElementById('chat-reply');
    const reply = input.value.trim();
    if (!reply) return;

    input.value = '';
    addChatMsg('user', reply);
    const assistantEl = addChatMsg('assistant', '', true);

    btnReply.disabled = true;
    streamSSE(
        '/api/braindump/reply',
        { reply, session_id: sessionId },
        text => {
            assistantEl.textContent += text;
            scrollChat();
        },
        data => {
            if (data.done) {
                assistantEl.classList.remove('streaming');
                btnReply.disabled = false;
            }
        }
    );
}

btnDone.addEventListener('click', () => {
    document.getElementById('dump-chat').classList.add('hidden');
    document.getElementById('dump-review').classList.remove('hidden');

    const preview = document.getElementById('polished-preview');
    preview.textContent = '';
    polishedText = '';

    streamSSE(
        '/api/braindump/polish',
        { session_id: sessionId },
        text => {
            polishedText += text;
            preview.textContent = polishedText;
        },
        () => {}
    );
});

btnEditToggle.addEventListener('click', () => {
    const preview = document.getElementById('polished-preview');
    const editArea = document.getElementById('polished-edit');
    editing = !editing;

    if (editing) {
        editArea.value = polishedText;
        editArea.classList.remove('hidden');
        preview.classList.add('hidden');
        btnEditToggle.textContent = 'Preview';
    } else {
        polishedText = editArea.value;
        preview.textContent = polishedText;
        editArea.classList.add('hidden');
        preview.classList.remove('hidden');
        btnEditToggle.textContent = 'Edit';
    }
});

btnSave.addEventListener('click', async () => {
    if (editing) {
        polishedText = document.getElementById('polished-edit').value;
    }

    btnSave.disabled = true;
    btnSave.textContent = 'Saving...';
    try {
        const res = await fetch('/api/entries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ polished_text: polishedText, session_id: sessionId }),
        });
        if (!res.ok) throw new Error('Save failed');
        btnSave.textContent = 'Saved';
        setTimeout(resetDump, 900);
    } catch {
        btnSave.textContent = 'Error saving';
        btnSave.disabled = false;
    }
});

btnNew.addEventListener('click', resetDump);

function resetDump() {
    document.getElementById('dump-input').classList.remove('hidden');
    document.getElementById('dump-chat').classList.add('hidden');
    document.getElementById('dump-review').classList.add('hidden');
    document.getElementById('raw-dump').value = '';
    document.getElementById('chat-messages').innerHTML = '';
    document.getElementById('polished-preview').textContent = '';
    document.getElementById('polished-edit').value = '';

    btnStart.disabled = false;
    btnSave.disabled = false;
    btnSave.textContent = 'Save Entry';

    editing = false;
    polishedText = '';
    sessionId = 'session_' + Date.now();

    document.getElementById('polished-edit').classList.add('hidden');
    document.getElementById('polished-preview').classList.remove('hidden');
    btnEditToggle.textContent = 'Edit';
}

function addChatMsg(role, text, streaming = false) {
    const el = document.createElement('div');
    el.className = 'chat-msg ' + role + (streaming ? ' streaming' : '');
    el.textContent = text;
    document.getElementById('chat-messages').appendChild(el);
    scrollChat();
    return el;
}

function scrollChat() {
    const box = document.getElementById('chat-messages');
    box.scrollTop = box.scrollHeight;
}

document.getElementById('btn-search').addEventListener('click', doSearch);
document.getElementById('search-query').addEventListener('keydown', e => {
    if (e.key === 'Enter') doSearch();
});

function doSearch() {
    const query = document.getElementById('search-query').value.trim();
    if (!query) return;

    const resultsDiv = document.getElementById('search-results');
    const refsDiv = document.getElementById('search-refs');
    const answerDiv = document.getElementById('search-answer');

    resultsDiv.classList.remove('hidden');
    refsDiv.innerHTML = '';
    answerDiv.textContent = '';

    let referencesShown = false;

    streamSSE(
        '/api/search',
        { query },
        text => {
            answerDiv.textContent += text;
        },
        data => {
            if (data.results && !referencesShown) {
                referencesShown = true;
                data.results.forEach(r => {
                    const span = document.createElement('span');
                    span.className = 'search-ref';
                    span.textContent = r.title || ('Entry #' + r.id);
                    refsDiv.appendChild(span);
                });
            }
        }
    );
}

async function loadEntries() {
    const list = document.getElementById('entries-list');
    const detail = document.getElementById('entry-detail');
    detail.classList.add('hidden');
    detail.innerHTML = '';
    list.classList.remove('hidden');

    try {
        const res = await fetch('/api/entries');
        const entries = await res.json();

        if (!entries.length) {
            list.innerHTML = '<div class="empty-state">No entries yet. Write your first brain dump.</div>';
            return;
        }

        list.innerHTML = entries.map(e => `
            <article class="entry-card" data-id="${e.id}">
                <h3>${escapeHtml(e.title)}</h3>
                <div class="meta">
                    ${e.mood ? '<span class="mood-tag">' + escapeHtml(e.mood) + '</span>' : ''}
                    ${e.tags ? escapeHtml(e.tags) : ''}
                    <span class="date">${formatDate(e.created_at)}</span>
                </div>
            </article>
        `).join('');

        list.querySelectorAll('.entry-card').forEach(card => {
            card.addEventListener('click', () => showEntry(card.dataset.id));
        });
    } catch {
        list.innerHTML = '<div class="empty-state">Error loading entries.</div>';
    }
}

async function showEntry(id) {
    const list = document.getElementById('entries-list');
    const detail = document.getElementById('entry-detail');
    try {
        const res = await fetch('/api/entries/' + id);
        const entry = await res.json();

        detail.innerHTML = `
            <h3 style="margin:0 0 8px;font-size:1.1rem;font-weight:600;">${escapeHtml(entry.title)}</h3>
            <div class="meta" style="margin-bottom:14px;">
                ${entry.mood ? '<span class="mood-tag">' + escapeHtml(entry.mood) + '</span>' : ''}
                ${entry.tags ? escapeHtml(entry.tags) : ''}
                <span class="date">${formatDate(entry.created_at)}</span>
            </div>
            <div class="body">${escapeHtml(entry.body)}</div>
            <div class="detail-actions">
                <button class="btn btn-secondary" id="btn-back">Back</button>
                <button class="btn btn-danger" id="btn-delete">Delete</button>
            </div>
        `;
        list.classList.add('hidden');
        detail.classList.remove('hidden');

        document.getElementById('btn-back').addEventListener('click', () => {
            detail.classList.add('hidden');
            list.classList.remove('hidden');
        });
        document.getElementById('btn-delete').addEventListener('click', () => deleteEntry(entry.id));
    } catch {
        detail.innerHTML = '<div class="empty-state">Error loading entry.</div>';
        list.classList.add('hidden');
        detail.classList.remove('hidden');
    }
}

async function deleteEntry(id) {
    if (!confirm('Delete this entry?')) return;
    await fetch('/api/entries/' + id, { method: 'DELETE' });
    document.getElementById('entry-detail').classList.add('hidden');
    loadEntries();
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text || '';
    return d.innerHTML;
}

function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
}
