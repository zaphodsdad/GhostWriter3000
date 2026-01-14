// Prose Pipeline - Frontend Application

// ============================================
// State
// ============================================
let currentProject = null;
let projects = [];
let characters = [];
let worlds = [];
let acts = [];
let chapters = [];
let scenes = [];
let currentGenId = null;
let pollingInterval = null;
let currentGenModel = null;
let currentCritiqueModel = null;
let sidebarCollapsed = false;
let currentReadingData = null;
let previousView = null;

// Chat state
let currentChatScope = null;
let currentChatScopeId = null;
let currentConversation = null;
let chatSending = false;

// Style guide state
let styleGuide = null;

// Queue state
let queueData = [];
let queuePollingInterval = null;
let currentQueueReviewIndex = 0;
let selectedScenes = new Set();
let previousQueueCount = 0;

// Settings state
let settingsModalOpen = false;

// Series state
let seriesList = [];
let currentSeries = null;

// Reference library state
let projectReferences = [];
let seriesReferences = [];

// ============================================
// Settings Modal
// ============================================
function toggleSettingsModal() {
    const modal = document.getElementById('settings-modal');
    settingsModalOpen = !settingsModalOpen;

    if (settingsModalOpen) {
        modal.style.display = 'flex';
        loadSettings();
    } else {
        modal.style.display = 'none';
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();

        // Update status indicators
        updateKeyStatus('openrouter', data.openrouter_api_key_set);
        updateKeyStatus('anthropic', data.anthropic_api_key_set);

        // Load custom endpoint if set
        if (data.custom_endpoint_url) {
            document.getElementById('settings-custom-url').value = data.custom_endpoint_url;
        }

        // Load data directory info
        if (data.data_dir) {
            document.getElementById('settings-data-dir-current').textContent = data.data_dir;
        }
        if (data.data_dir_from) {
            const sourceEl = document.getElementById('settings-data-dir-source');
            sourceEl.textContent = data.data_dir_from;
            sourceEl.className = 'badge' + (data.data_dir_from === 'config' ? ' canon' : '');
        }

        // Clear the input fields (we don't send back actual keys for security)
        document.getElementById('settings-openrouter-key').value = '';
        document.getElementById('settings-anthropic-key').value = '';
        document.getElementById('settings-custom-key').value = '';
        document.getElementById('settings-data-dir').value = '';
        document.getElementById('data-dir-status').textContent = '';

    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

function updateKeyStatus(provider, isSet) {
    const statusEl = document.getElementById(`${provider}-key-status`);
    if (isSet) {
        statusEl.textContent = 'Key is configured';
        statusEl.className = 'key-status set';
    } else {
        statusEl.textContent = 'No key set';
        statusEl.className = 'key-status not-set';
    }
}

async function saveSettings() {
    const openrouterKey = document.getElementById('settings-openrouter-key').value.trim();
    const anthropicKey = document.getElementById('settings-anthropic-key').value.trim();
    const customUrl = document.getElementById('settings-custom-url').value.trim();
    const customKey = document.getElementById('settings-custom-key').value.trim();

    // Build update object - only include non-empty values
    const update = {};
    if (openrouterKey) update.openrouter_api_key = openrouterKey;
    if (anthropicKey) update.anthropic_api_key = anthropicKey;
    if (customUrl) update.custom_endpoint_url = customUrl;
    if (customKey) update.custom_endpoint_key = customKey;

    // Don't send empty request
    if (Object.keys(update).length === 0) {
        showToast('Info', 'No changes to save', 'info');
        toggleSettingsModal();
        return;
    }

    try {
        const response = await fetch('/api/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update)
        });

        if (response.ok) {
            showToast('Success', 'Settings saved successfully', 'success');
            toggleSettingsModal();
        } else {
            const error = await response.json();
            showToast('Error', `Failed to save: ${error.detail || 'Unknown error'}`, 'error');
        }
    } catch (e) {
        console.error('Failed to save settings:', e);
        showToast('Error', 'Failed to save settings', 'error');
    }
}

function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const btn = input.nextElementSibling;

    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = 'Hide';
    } else {
        input.type = 'password';
        btn.textContent = 'Show';
    }
}

async function saveDataDir() {
    const newPath = document.getElementById('settings-data-dir').value.trim();
    const statusEl = document.getElementById('data-dir-status');

    if (!newPath) {
        statusEl.textContent = 'Please enter a path';
        statusEl.className = 'key-status not-set';
        return;
    }

    try {
        const response = await fetch('/api/settings/data-dir', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_dir: newPath })
        });

        const data = await response.json();

        if (response.ok) {
            statusEl.textContent = 'Saved! Restart server to apply.';
            statusEl.className = 'key-status set';
            showToast('Success', data.message, 'success');

            // Update the display
            document.getElementById('settings-data-dir-current').textContent = data.data_dir;
            document.getElementById('settings-data-dir-source').textContent = 'config (pending restart)';
            document.getElementById('settings-data-dir').value = '';
        } else {
            statusEl.textContent = data.detail || 'Failed to save';
            statusEl.className = 'key-status not-set';
            showToast('Error', data.detail || 'Failed to save data directory', 'error');
        }
    } catch (e) {
        console.error('Failed to save data directory:', e);
        statusEl.textContent = 'Error saving';
        statusEl.className = 'key-status not-set';
        showToast('Error', 'Failed to save data directory', 'error');
    }
}

// ============================================
// API Base URL Helper
// ============================================
function apiUrl(path) {
    if (currentProject) {
        return `/api/projects/${currentProject.id}${path}`;
    }
    return `/api${path}`;
}

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadSeries();
    loadProjects();
    setInterval(checkHealth, 30000);

    // Back to top button scroll listener
    const backToTopBtn = document.getElementById('back-to-top');
    if (backToTopBtn) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 300) {
                backToTopBtn.classList.add('visible');
            } else {
                backToTopBtn.classList.remove('visible');
            }
        });
    }
});

// Scroll to top function
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// ============================================
// Health Check
// ============================================
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        const el = document.getElementById('health-status');
        if (data.status === 'healthy') {
            el.textContent = 'Connected';
            el.className = 'health-status online';
        } else {
            el.textContent = 'Unhealthy';
            el.className = 'health-status offline';
        }
    } catch (e) {
        const el = document.getElementById('health-status');
        el.textContent = 'Offline';
        el.className = 'health-status offline';
    }
}

// ============================================
// Project Management
// ============================================
async function loadProjects() {
    try {
        const response = await fetch('/api/projects/');
        projects = await response.json();
        renderProjects();
        renderSeriesList(); // Re-render series to show nested books
    } catch (e) {
        console.error('Failed to load projects:', e);
        document.getElementById('projects-list').innerHTML =
            '<div class="empty-state">Failed to load projects</div>';
    }
}

function renderProjects() {
    const list = document.getElementById('projects-list');

    // Filter by selected series if one is selected
    let filteredProjects = projects;
    if (currentSeries) {
        filteredProjects = projects.filter(p => p.series_id === currentSeries.id);
    }

    // Update clear series button visibility
    const clearBtn = document.getElementById('clear-series-btn');
    if (clearBtn) {
        clearBtn.style.display = currentSeries ? 'inline-flex' : 'none';
    }

    if (filteredProjects.length === 0) {
        const msg = currentSeries
            ? `No books in "${currentSeries.title}" yet. Create one to get started!`
            : 'No projects yet. Create your first project to get started!';
        list.innerHTML = `<div class="empty-state">${msg}</div>`;
        return;
    }

    list.innerHTML = filteredProjects.map(p => {
        // Find series name if project is in a series
        const series = seriesList.find(s => s.id === p.series_id);
        const seriesBadge = series && p.book_number
            ? `<span class="badge series-badge">Book ${p.book_number}</span>`
            : series
                ? `<span class="badge series-badge">${escapeHtml(series.title)}</span>`
                : '';

        return `
            <div class="item" onclick="selectProject('${p.id}')" style="cursor: pointer;">
                <div class="item-header">
                    <div class="item-title">${escapeHtml(p.title)}</div>
                    <div class="item-actions">
                        <button class="btn btn-danger" onclick="event.stopPropagation(); deleteProject('${p.id}')">Delete</button>
                    </div>
                </div>
                <div class="item-meta">
                    ${seriesBadge}
                    ${p.genre ? `<span class="badge">${escapeHtml(p.genre)}</span>` : ''}
                    <span class="badge">${p.character_count} characters</span>
                    <span class="badge">${p.scene_count} scenes</span>
                    ${p.canon_scene_count > 0 ? `<span class="badge canon">${p.canon_scene_count} canon</span>` : ''}
                </div>
                ${p.description ? `<div class="item-content">${escapeHtml(p.description)}</div>` : ''}
            </div>
        `;
    }).join('');
}

function showNewProjectForm() {
    document.getElementById('new-project-form').style.display = 'block';

    // Populate series select
    const seriesSelect = document.getElementById('project-series');
    seriesSelect.innerHTML = '<option value="">-- Standalone Project --</option>' +
        seriesList.map(s => `<option value="${s.id}">${escapeHtml(s.title)}</option>`).join('');

    // If a series is currently selected, pre-select it
    if (currentSeries) {
        seriesSelect.value = currentSeries.id;
        document.getElementById('book-number-group').style.display = 'block';
    }

    // Add change handler for series select
    seriesSelect.onchange = function() {
        const bookNumGroup = document.getElementById('book-number-group');
        bookNumGroup.style.display = this.value ? 'block' : 'none';
    };

    document.getElementById('project-title').focus();
}

function hideNewProjectForm() {
    document.getElementById('new-project-form').style.display = 'none';
    document.getElementById('project-title').value = '';
    document.getElementById('project-description').value = '';
    document.getElementById('project-author').value = '';
    document.getElementById('project-genre').value = '';
    document.getElementById('project-series').value = '';
    document.getElementById('project-book-number').value = '';
    document.getElementById('book-number-group').style.display = 'none';
}

async function createProject(e) {
    e.preventDefault();

    const title = document.getElementById('project-title').value.trim();
    const description = document.getElementById('project-description').value.trim();
    const author = document.getElementById('project-author').value.trim();
    const genre = document.getElementById('project-genre').value.trim();
    const seriesId = document.getElementById('project-series').value || null;
    const bookNumber = document.getElementById('project-book-number').value;

    if (!title) {
        alert('Please enter a book title');
        return;
    }

    try {
        const projectData = { title, description, author, genre };
        if (seriesId) {
            projectData.series_id = seriesId;
            if (bookNumber) {
                projectData.book_number = parseInt(bookNumber);
            }
        }

        const response = await fetch('/api/projects/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projectData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create project');
        }

        const project = await response.json();

        // If added to a series, update the series to include this project
        if (seriesId) {
            try {
                await fetch(`/api/series/${seriesId}/books`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: project.id,
                        book_number: bookNumber ? parseInt(bookNumber) : null
                    })
                });
            } catch (err) {
                console.error('Failed to add project to series:', err);
            }
        }

        hideNewProjectForm();
        await loadSeries(); // Refresh series list
        selectProject(project.id);
    } catch (e) {
        alert('Error creating book: ' + e.message);
    }
}

async function deleteProject(projectId) {
    if (!confirm('Are you sure you want to delete this book? This will delete all characters, worlds, and scenes.')) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete project');
        }

        await loadProjects();
    } catch (e) {
        alert('Error deleting book: ' + e.message);
    }
}

async function selectProject(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}`);
        currentProject = await response.json();

        // Update UI
        document.getElementById('project-selector').classList.remove('active');
        document.getElementById('main-app').style.display = 'block';
        document.getElementById('current-project-title').textContent = currentProject.title;
        document.getElementById('current-project-description').textContent =
            currentProject.description || 'No description';

        // Show series info if project is in a series
        updateProjectSeriesDisplay();

        // Setup navigation and load data
        setupNavigation();
        await loadAllData();
    } catch (e) {
        alert('Error loading book: ' + e.message);
    }
}

function switchProject() {
    currentProject = null;
    characters = [];
    worlds = [];
    acts = [];
    chapters = [];
    scenes = [];

    document.getElementById('main-app').style.display = 'none';
    document.getElementById('project-selector').classList.add('active');

    loadProjects();
}

// ============================================
// Clear Project Structure
// ============================================
async function confirmClearStructure() {
    // Triple confirmation for safety
    const projectTitle = currentProject?.title || 'this project';

    const confirm1 = confirm(
        `WARNING: This will delete ALL acts, chapters, scenes, and generations from "${projectTitle}".\n\n` +
        `Characters, world, style, and references will be preserved.\n\n` +
        `Are you sure you want to continue?`
    );
    if (!confirm1) return;

    const confirm2 = confirm(
        `SECOND CONFIRMATION:\n\n` +
        `You are about to permanently delete the entire story structure.\n` +
        `This cannot be undone.\n\n` +
        `Type OK to confirm you want to clear "${projectTitle}".`
    );
    if (!confirm2) return;

    const confirm3 = prompt(
        `FINAL CONFIRMATION:\n\n` +
        `Type "DELETE" (all caps) to permanently clear the project structure:`
    );
    if (confirm3 !== 'DELETE') {
        alert('Clear cancelled. You must type DELETE exactly.');
        return;
    }

    try {
        const response = await fetch(apiUrl('/structure'), {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to clear structure');
        }

        const result = await response.json();
        showToast('Success',
            `Cleared: ${result.deleted.acts} acts, ${result.deleted.chapters} chapters, ${result.deleted.scenes} scenes`,
            'success'
        );

        // Reload data
        await loadAllData();

    } catch (e) {
        alert('Error clearing structure: ' + e.message);
    }
}

// ============================================
// Move to Series
// ============================================
function showMoveToSeriesModal() {
    const modal = document.getElementById('move-series-modal');
    const select = document.getElementById('move-series-select');

    // Populate series dropdown
    select.innerHTML = '<option value="">-- No Series (Standalone) --</option>' +
        seriesList.map(s => `<option value="${s.id}">${escapeHtml(s.title)}</option>`).join('');

    // Pre-select current series if any
    if (currentProject?.series_id) {
        select.value = currentProject.series_id;
        document.getElementById('move-book-number-group').style.display = 'block';
        document.getElementById('move-book-number').value = currentProject.book_number || '';
    } else {
        document.getElementById('move-book-number-group').style.display = 'none';
    }

    // Add change handler
    select.onchange = function() {
        document.getElementById('move-book-number-group').style.display = this.value ? 'block' : 'none';
    };

    modal.style.display = 'flex';
}

function hideMoveToSeriesModal() {
    document.getElementById('move-series-modal').style.display = 'none';
}

async function moveProjectToSeries() {
    const seriesId = document.getElementById('move-series-select').value || null;
    const bookNumber = document.getElementById('move-book-number').value;

    try {
        const response = await fetch(apiUrl('/series'), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                series_id: seriesId,
                book_number: bookNumber ? parseInt(bookNumber) : null
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to move project');
        }

        // Update local state
        currentProject.series_id = seriesId;
        currentProject.book_number = bookNumber ? parseInt(bookNumber) : null;

        // Update UI
        updateProjectSeriesDisplay();
        hideMoveToSeriesModal();
        await loadSeries(); // Refresh series list

        showToast('Success', seriesId ? 'Project moved to series' : 'Project removed from series', 'success');

    } catch (e) {
        alert('Error moving book: ' + e.message);
    }
}

function updateProjectSeriesDisplay() {
    const infoDiv = document.getElementById('project-series-info');
    const badge = document.getElementById('project-series-badge');

    if (currentProject?.series_id) {
        const series = seriesList.find(s => s.id === currentProject.series_id);
        if (series) {
            const bookNum = currentProject.book_number ? ` - Book ${currentProject.book_number}` : '';
            badge.textContent = `${series.title}${bookNum}`;
            infoDiv.style.display = 'block';
        } else {
            infoDiv.style.display = 'none';
        }
    } else {
        infoDiv.style.display = 'none';
    }
}

// ============================================
// Series Management
// ============================================
async function loadSeries() {
    try {
        const response = await fetch('/api/series/');
        seriesList = await response.json();
        renderSeriesList();
    } catch (e) {
        console.error('Failed to load series:', e);
    }
}

function renderSeriesList() {
    const list = document.getElementById('series-list');
    if (!list) return;

    let html = '';

    // Render each series with nested books
    html += seriesList.map(s => {
        const seriesBooks = projects.filter(p => p.series_id === s.id);
        seriesBooks.sort((a, b) => (a.book_number || 999) - (b.book_number || 999));

        const booksHtml = seriesBooks.length > 0
            ? `<div class="series-books">
                ${seriesBooks.map(book => `
                    <div class="series-book" onclick="event.stopPropagation(); selectProject('${book.id}')">
                        <span class="book-number">${book.book_number ? `Book ${book.book_number}:` : ''}</span>
                        <span class="book-title">${escapeHtml(book.title)}</span>
                        <span class="book-stats">${book.scene_count} scenes${book.canon_scene_count > 0 ? `, ${book.canon_scene_count} canon` : ''}</span>
                    </div>
                `).join('')}
               </div>`
            : '<div class="series-books empty">No books yet</div>';

        return `
            <div class="item series-item ${currentSeries?.id === s.id ? 'selected' : ''}">
                <div class="item-header" onclick="selectSeries('${s.id}')" style="cursor: pointer;">
                    <div class="item-title">${escapeHtml(s.title)}</div>
                    <div class="item-actions">
                        <span class="badge">${seriesBooks.length} books</span>
                        ${s.genre ? `<span class="badge">${escapeHtml(s.genre)}</span>` : ''}
                        <button class="btn btn-small btn-danger" onclick="event.stopPropagation(); deleteSeries('${s.id}')">Delete</button>
                    </div>
                </div>
                ${s.description ? `<div class="item-content" style="margin: 8px 0;">${escapeHtml(s.description.substring(0, 200))}...</div>` : ''}
                ${booksHtml}
            </div>
        `;
    }).join('');

    // Render standalone books (not in any series)
    const standaloneBooks = projects.filter(p => !p.series_id);
    if (standaloneBooks.length > 0) {
        html += `
            <div class="item series-item standalone-section">
                <div class="item-header">
                    <div class="item-title">Standalone Books</div>
                    <div class="item-actions">
                        <span class="badge">${standaloneBooks.length} books</span>
                    </div>
                </div>
                <div class="series-books">
                    ${standaloneBooks.map(book => `
                        <div class="series-book" onclick="selectProject('${book.id}')">
                            <span class="book-title">${escapeHtml(book.title)}</span>
                            <span class="book-stats">${book.scene_count} scenes${book.canon_scene_count > 0 ? `, ${book.canon_scene_count} canon` : ''}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    if (!html) {
        list.innerHTML = '<div class="empty-state">No books yet. Create a series or standalone book to get started.</div>';
        return;
    }

    list.innerHTML = html;
}

function showNewSeriesForm() {
    document.getElementById('new-series-form').style.display = 'block';
    document.getElementById('series-title').focus();
}

function hideNewSeriesForm() {
    document.getElementById('new-series-form').style.display = 'none';
    document.getElementById('series-title').value = '';
    document.getElementById('series-description').value = '';
    document.getElementById('series-author').value = '';
    document.getElementById('series-genre').value = '';
}

async function createSeries(e) {
    e.preventDefault();

    const title = document.getElementById('series-title').value.trim();
    const description = document.getElementById('series-description').value.trim();
    const author = document.getElementById('series-author').value.trim();
    const genre = document.getElementById('series-genre').value.trim();

    if (!title) {
        alert('Please enter a series title');
        return;
    }

    try {
        const response = await fetch('/api/series/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description, author, genre })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create series');
        }

        hideNewSeriesForm();
        await loadSeries();
    } catch (e) {
        alert('Error creating series: ' + e.message);
    }
}

async function deleteSeries(seriesId) {
    if (!confirm('Delete this series? Books will be unlinked but not deleted.')) return;

    try {
        await fetch(`/api/series/${seriesId}`, { method: 'DELETE' });
        if (currentSeries?.id === seriesId) {
            currentSeries = null;
        }
        await loadSeries();
        await loadProjects();
    } catch (e) {
        alert('Error deleting series: ' + e.message);
    }
}

async function selectSeries(seriesId) {
    try {
        const response = await fetch(`/api/series/${seriesId}`);
        currentSeries = await response.json();
        renderSeriesList();
        await loadProjects(); // Reload to filter by series if needed
    } catch (e) {
        alert('Error loading series: ' + e.message);
    }
}

function clearSeriesSelection() {
    currentSeries = null;
    renderSeriesList();
    loadProjects();
}

// ============================================
// Reference Library
// ============================================
async function loadReferences() {
    if (!currentProject) return;

    try {
        // Load project references
        const projResponse = await fetch(apiUrl('/references/'));
        projectReferences = await projResponse.json();

        // Load series references if project is in a series
        if (currentProject.series_id) {
            const seriesResponse = await fetch(`/api/series/${currentProject.series_id}/references/`);
            seriesReferences = await seriesResponse.json();
        } else {
            seriesReferences = [];
        }

        renderReferences();
    } catch (e) {
        console.error('Failed to load references:', e);
    }
}

function renderReferences() {
    const list = document.getElementById('references-list');
    if (!list) return;

    const allRefs = [
        ...seriesReferences.map(r => ({ ...r, scope: 'series' })),
        ...projectReferences.map(r => ({ ...r, scope: 'project' }))
    ];

    if (allRefs.length === 0) {
        list.innerHTML = '<div class="empty-state">No reference documents yet. Upload style guides, published books, or notes to help the AI.</div>';
        return;
    }

    const docTypeLabels = {
        'style_reference': 'Style Reference',
        'published_book': 'Published Book',
        'world_notes': 'World Notes',
        'character_notes': 'Character Notes',
        'research': 'Research',
        'other': 'Other'
    };

    list.innerHTML = allRefs.map(r => `
        <div class="item reference-item">
            <div class="item-header">
                <div class="item-title">${escapeHtml(r.title)}</div>
                <div class="item-actions">
                    <span class="badge ${r.scope === 'series' ? 'series-badge' : ''}">${r.scope}</span>
                    <button class="btn btn-small btn-danger" onclick="deleteReference('${r.id}', '${r.scope}')">Delete</button>
                </div>
            </div>
            <div class="item-meta">
                <span class="badge">${docTypeLabels[r.doc_type] || r.doc_type}</span>
                <span class="badge">${r.word_count?.toLocaleString() || 0} words</span>
                ${r.use_in_generation ? '<span class="badge canon">Gen</span>' : ''}
                ${r.use_in_chat ? '<span class="badge">Chat</span>' : ''}
            </div>
            ${r.description ? `<div class="item-content">${escapeHtml(r.description)}</div>` : ''}
        </div>
    `).join('');
}

function showNewReferenceForm() {
    document.getElementById('reference-form').style.display = 'block';
    document.getElementById('ref-title').focus();
}

function hideReferenceForm() {
    document.getElementById('reference-form').style.display = 'none';
    document.getElementById('ref-title').value = '';
    document.getElementById('ref-description').value = '';
    document.getElementById('ref-type').value = 'other';
    document.getElementById('ref-content').value = '';
    document.getElementById('ref-file').value = '';
    document.getElementById('ref-file-name').textContent = '';
    document.getElementById('ref-word-count').textContent = '';
    document.getElementById('ref-use-generation').checked = true;
    document.getElementById('ref-use-chat').checked = true;
}

function handleReferenceFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['.txt', '.md', '.markdown'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validTypes.includes(ext)) {
        alert('Please upload a .txt or .md file');
        event.target.value = '';
        return;
    }

    // Read file content
    const reader = new FileReader();
    reader.onload = function(e) {
        const content = e.target.result;
        document.getElementById('ref-content').value = content;
        document.getElementById('ref-file-name').textContent = `Loaded: ${file.name}`;

        // Update word count
        const wordCount = content.split(/\s+/).filter(w => w.length > 0).length;
        document.getElementById('ref-word-count').textContent = `${wordCount.toLocaleString()} words`;

        // Auto-fill title if empty
        const titleInput = document.getElementById('ref-title');
        if (!titleInput.value) {
            // Use filename without extension as title
            titleInput.value = file.name.replace(/\.[^/.]+$/, '');
        }
    };
    reader.onerror = function() {
        alert('Error reading file');
    };
    reader.readAsText(file);
}

// Update word count on paste/type
document.addEventListener('DOMContentLoaded', function() {
    const refContent = document.getElementById('ref-content');
    if (refContent) {
        refContent.addEventListener('input', function() {
            const wordCount = this.value.split(/\s+/).filter(w => w.length > 0).length;
            document.getElementById('ref-word-count').textContent = wordCount > 0 ? `${wordCount.toLocaleString()} words` : '';
        });
    }
});

async function saveReference(e) {
    e.preventDefault();

    const title = document.getElementById('ref-title').value.trim();
    const description = document.getElementById('ref-description').value.trim();
    const docType = document.getElementById('ref-type').value;
    const content = document.getElementById('ref-content').value.trim();
    const useInGeneration = document.getElementById('ref-use-generation').checked;
    const useInChat = document.getElementById('ref-use-chat').checked;

    if (!title || !content) {
        alert('Please enter a title and content');
        return;
    }

    try {
        const response = await fetch(apiUrl('/references/'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title,
                description: description || undefined,
                doc_type: docType,
                content,
                use_in_generation: useInGeneration,
                use_in_chat: useInChat
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save reference');
        }

        hideReferenceForm();
        await loadReferences();
        showToast('Success', 'Reference document saved', 'success');
    } catch (e) {
        alert('Error saving reference: ' + e.message);
    }
}

async function deleteReference(refId, scope) {
    if (!confirm('Delete this reference document?')) return;

    try {
        const url = scope === 'series' && currentProject?.series_id
            ? `/api/series/${currentProject.series_id}/references/${refId}`
            : apiUrl(`/references/${refId}`);

        await fetch(url, { method: 'DELETE' });
        await loadReferences();
    } catch (e) {
        alert('Error deleting reference: ' + e.message);
    }
}

// ============================================
// Edit Mode
// ============================================
function showImportProseModal(sceneId) {
    const modal = document.getElementById('import-prose-modal');
    modal.style.display = 'flex';
    modal.dataset.sceneId = sceneId;
    document.getElementById('import-prose-text').value = '';
    document.getElementById('import-prose-text').focus();
}

function hideImportProseModal() {
    document.getElementById('import-prose-modal').style.display = 'none';
}

async function importProseForEdit() {
    const modal = document.getElementById('import-prose-modal');
    const sceneId = modal.dataset.sceneId;
    const prose = document.getElementById('import-prose-text').value.trim();

    if (!prose) {
        alert('Please paste or type the prose to import');
        return;
    }

    try {
        const response = await fetch(apiUrl(`/scenes/${sceneId}/edit-mode`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prose })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to import prose');
        }

        const result = await response.json();
        hideImportProseModal();
        await loadScenes();
        renderOutlineTree();
        renderStructureTree();
        showToast('Success', result.message, 'success');
    } catch (e) {
        alert('Error importing prose: ' + e.message);
    }
}

async function startEditModeGeneration(sceneId) {
    const genModel = document.getElementById('gen-model')?.value || null;
    const critiqueModel = document.getElementById('critique-model')?.value || null;

    try {
        const response = await fetch(apiUrl('/generations/start-edit'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scene_id: sceneId,
                max_iterations: 5,
                generation_model: genModel || undefined,
                critique_model: critiqueModel || undefined
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start edit mode');
        }

        const state = await response.json();
        currentGenId = state.generation_id;
        currentGenModel = genModel;
        currentCritiqueModel = critiqueModel;

        showGenStep('progress');
        startPolling();
    } catch (e) {
        alert('Error starting edit mode: ' + e.message);
    }
}

// ============================================
// Sidebar
// ============================================
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebarCollapsed = !sidebarCollapsed;
    if (sidebarCollapsed) {
        sidebar.classList.add('collapsed');
    } else {
        sidebar.classList.remove('collapsed');
    }
}

function renderOutlineTree() {
    const tree = document.getElementById('outline-tree');

    if (chapters.length === 0) {
        tree.innerHTML = '<div class="empty-state" style="padding: 20px;">No chapters yet</div>';
        return;
    }

    // Group chapters by act
    const actChapters = {};
    const noActChapters = [];

    chapters.forEach(ch => {
        if (ch.act_id) {
            if (!actChapters[ch.act_id]) actChapters[ch.act_id] = [];
            actChapters[ch.act_id].push(ch);
        } else {
            noActChapters.push(ch);
        }
    });

    let html = '';

    // Render acts with their chapters
    acts.forEach(act => {
        const actChapterList = actChapters[act.id] || [];
        html += `
            <div class="outline-act">
                <div class="outline-act-title" onclick="showReadingView('act', '${act.id}')">
                    ${escapeHtml(act.title)}
                </div>
                <div class="outline-chapters">
                    ${actChapterList.map(ch => renderOutlineChapter(ch)).join('')}
                </div>
            </div>
        `;
    });

    // Render chapters without acts
    if (noActChapters.length > 0) {
        html += `
            <div class="outline-chapters">
                ${noActChapters.map(ch => renderOutlineChapter(ch)).join('')}
            </div>
        `;
    }

    tree.innerHTML = html;
}

function renderOutlineChapter(chapter) {
    const chapterScenes = scenes.filter(s => s.chapter_id === chapter.id);
    chapterScenes.sort((a, b) => (a.scene_number || 0) - (b.scene_number || 0));

    const nonCanonCount = chapterScenes.filter(s => !s.is_canon).length;

    return `
        <div class="outline-chapter">
            <div class="outline-chapter-title" onclick="showReadingView('chapter', '${chapter.id}')">
                <span>Ch ${chapter.chapter_number}: ${escapeHtml(chapter.title)}</span>
                ${nonCanonCount > 0 ? `<button class="generate-chapter-btn" onclick="generateChapter('${chapter.id}', event)">Gen ${nonCanonCount}</button>` : ''}
            </div>
            <div class="outline-scenes">
                ${chapterScenes.map(s => `
                    <div class="outline-scene ${s.is_canon ? 'canon' : ''}" onclick="showReadingView('scene', '${s.id}')">
                        ${!s.is_canon ? `<input type="checkbox" class="batch-checkbox" ${selectedScenes.has(s.id) ? 'checked' : ''} onclick="toggleSceneSelection('${s.id}', event)">` : ''}
                        ${escapeHtml(s.title)}
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ============================================
// Navigation
// ============================================
function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            navigateToView(view);
        });
    });
}

async function navigateToView(view) {
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const activeBtn = document.querySelector(`.nav-btn[data-view="${view}"]`);
    if (activeBtn) activeBtn.classList.add('active');

    // Update views
    document.querySelectorAll('.main-content .view').forEach(v => v.classList.remove('active'));
    const viewEl = document.getElementById(`${view}-view`);
    if (viewEl) viewEl.classList.add('active');

    // Handle queue view
    if (view === 'queue') {
        await loadQueue();
        startQueuePolling();
    } else {
        // Keep polling in background for badge updates, but less frequently
        // stopQueuePolling(); // Uncomment to stop polling when not on queue view
    }

    // Handle references view
    if (view === 'references') {
        await loadReferences();
    }
}

// ============================================
// Data Loading
// ============================================
async function loadAllData() {
    await Promise.all([
        loadCharacters(),
        loadWorlds(),
        loadActs(),
        loadChapters(),
        loadScenes(),
        loadStyleGuide(),
        loadReferences()
    ]);
    updateStats();
    populateFormSelects();
    renderOutlineTree();
    renderStructureTree();
}

async function loadCharacters() {
    try {
        const response = await fetch(apiUrl('/characters/'));
        characters = await response.json();
        renderCharacters();
    } catch (e) {
        console.error('Failed to load characters:', e);
    }
}

async function loadWorlds() {
    try {
        const response = await fetch(apiUrl('/world/'));
        worlds = await response.json();
        renderWorlds();
    } catch (e) {
        console.error('Failed to load worlds:', e);
    }
}

async function loadActs() {
    try {
        const response = await fetch(apiUrl('/acts/'));
        acts = await response.json();
    } catch (e) {
        console.error('Failed to load acts:', e);
        acts = [];
    }
}

async function loadChapters() {
    try {
        const response = await fetch(apiUrl('/chapters/'));
        chapters = await response.json();
    } catch (e) {
        console.error('Failed to load chapters:', e);
        chapters = [];
    }
}

async function loadScenes() {
    try {
        const response = await fetch(apiUrl('/scenes/'));
        scenes = await response.json();
    } catch (e) {
        console.error('Failed to load scenes:', e);
    }
}

async function loadStyleGuide() {
    try {
        const response = await fetch(apiUrl('/style/'));
        styleGuide = await response.json();
        populateStyleForm();
    } catch (e) {
        console.error('Failed to load style guide:', e);
        styleGuide = { pov: '', tense: '', tone: '', heat_level: '', guide: '' };
    }
}

function populateStyleForm() {
    if (!styleGuide) return;

    document.getElementById('style-pov').value = styleGuide.pov || '';
    document.getElementById('style-tense').value = styleGuide.tense || '';
    document.getElementById('style-tone').value = styleGuide.tone || '';
    document.getElementById('style-heat').value = styleGuide.heat_level || '';
    document.getElementById('style-guide').value = styleGuide.guide || '';
}

async function saveStyleGuide() {
    const data = {
        pov: document.getElementById('style-pov').value || null,
        tense: document.getElementById('style-tense').value || null,
        tone: document.getElementById('style-tone').value || null,
        heat_level: document.getElementById('style-heat').value || null,
        guide: document.getElementById('style-guide').value || ''
    };

    try {
        const response = await fetch(apiUrl('/style/'), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Failed to save style guide');
        }

        styleGuide = await response.json();

        // Show save confirmation
        const status = document.getElementById('style-save-status');
        status.textContent = 'Style guide saved successfully!';
        status.style.color = 'var(--success)';
        setTimeout(() => {
            status.textContent = '';
        }, 3000);

    } catch (e) {
        alert('Error saving style guide: ' + e.message);
    }
}

function updateStats() {
    console.log('updateStats called');
    console.log('scenes count:', scenes.length);

    document.getElementById('stat-characters').textContent = characters.length;
    document.getElementById('stat-worlds').textContent = worlds.length;
    document.getElementById('stat-chapters').textContent = chapters.length;
    document.getElementById('stat-scenes').textContent = scenes.length;

    const canonScenes = scenes.filter(s => s.is_canon);
    console.log('canon scenes:', canonScenes.length, canonScenes.map(s => s.id));
    document.getElementById('stat-canon').textContent = canonScenes.length;

    // Calculate word count from canon scenes
    let wordCount = 0;
    canonScenes.forEach(s => {
        console.log(`Scene ${s.id}: prose=${s.prose ? s.prose.length + ' chars' : 'null'}`);
        if (s.prose) {
            wordCount += s.prose.split(/\s+/).length;
        }
    });
    console.log('Total word count:', wordCount);
    document.getElementById('stat-words').textContent = wordCount.toLocaleString();

    // Update master word count in header
    document.getElementById('master-word-count').textContent = wordCount.toLocaleString();
}

function populateFormSelects() {
    // Character select for scenes
    const charSelect = document.getElementById('scene-characters');
    if (charSelect) {
        charSelect.innerHTML = characters.map(c =>
            `<option value="${c.id}">${escapeHtml(c.metadata?.name || c.id)}</option>`
        ).join('');
    }

    // World select for scenes
    const worldSelect = document.getElementById('scene-world');
    if (worldSelect) {
        worldSelect.innerHTML = '<option value="">-- Select World --</option>' +
            worlds.map(w =>
                `<option value="${w.id}">${escapeHtml(w.metadata?.name || w.id)}</option>`
            ).join('');
    }

    // Previous scenes select
    const prevSelect = document.getElementById('scene-previous');
    if (prevSelect) {
        prevSelect.innerHTML = scenes.filter(s => s.is_canon).map(s =>
            `<option value="${s.id}">${escapeHtml(s.title)}</option>`
        ).join('');
    }

    // Chapter select for scenes
    const chapterSelect = document.getElementById('scene-chapter');
    if (chapterSelect) {
        chapterSelect.innerHTML = '<option value="">-- Select Chapter --</option>' +
            chapters.map(ch =>
                `<option value="${ch.id}">Ch ${ch.chapter_number}: ${escapeHtml(ch.title)}</option>`
            ).join('');
    }

    // Act select for chapters
    const actSelect = document.getElementById('chapter-act');
    if (actSelect) {
        actSelect.innerHTML = '<option value="">-- No Act --</option>' +
            acts.map(a =>
                `<option value="${a.id}">${escapeHtml(a.title)}</option>`
            ).join('');
    }

    // Scene select for generation
    const genSelect = document.getElementById('gen-scene-select');
    if (genSelect) {
        genSelect.innerHTML = '<option value="">-- Choose a Scene --</option>' +
            scenes.filter(s => !s.is_canon).map(s => {
                const chapter = chapters.find(ch => ch.id === s.chapter_id);
                const chapterLabel = chapter ? `Ch ${chapter.chapter_number}: ` : '';
                return `<option value="${s.id}">${chapterLabel}${escapeHtml(s.title)}</option>`;
            }).join('');
    }

    // Chat scope select
    populateChatScopeSelect();
}

// ============================================
// Render Functions
// ============================================
function renderCharacters() {
    const list = document.getElementById('characters-list');

    if (characters.length === 0) {
        list.innerHTML = '<div class="empty-state">No characters yet. Create your first character!</div>';
        return;
    }

    list.innerHTML = characters.map(c => `
        <div class="item character-item">
            <div class="character-portrait-thumb" onclick="showCharacterDetail('${c.id}')">
                ${c.metadata?.portrait
                    ? `<img src="${apiUrl(`/characters/${c.id}/portrait`)}" alt="${escapeHtml(c.metadata?.name || '')}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                       <div class="portrait-fallback" style="display: none;">${escapeHtml((c.metadata?.name || 'C').charAt(0))}</div>`
                    : `<div class="portrait-fallback">${escapeHtml((c.metadata?.name || 'C').charAt(0))}</div>`
                }
            </div>
            <div class="character-info">
                <div class="item-header">
                    <div class="item-title">${escapeHtml(c.metadata?.name || c.id)}</div>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-secondary" onclick="showCharacterDetail('${c.id}')">View</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteCharacter('${c.id}')">Delete</button>
                    </div>
                </div>
                <div class="item-meta">
                    ${c.metadata?.role ? `<span class="badge">${escapeHtml(c.metadata.role)}</span>` : ''}
                    ${c.metadata?.age ? `<span class="badge">Age: ${c.metadata.age}</span>` : ''}
                    ${c.metadata?.occupation ? `<span class="badge">${escapeHtml(c.metadata.occupation)}</span>` : ''}
                </div>
                ${c.metadata?.background ? `<div class="item-content">${escapeHtml(c.metadata.background.substring(0, 200))}...</div>` : ''}
            </div>
        </div>
    `).join('');
}

async function showCharacterDetail(characterId) {
    const character = characters.find(c => c.id === characterId);
    if (!character) {
        console.error('Character not found:', characterId);
        return;
    }

    // Populate form with existing data
    editingCharacterId = characterId;
    document.getElementById('character-form-title').textContent = 'Edit Character';
    document.getElementById('char-name').value = character.metadata?.name || '';
    document.getElementById('char-role').value = character.metadata?.role || '';
    document.getElementById('char-age').value = character.metadata?.age || '';
    document.getElementById('char-occupation').value = character.metadata?.occupation || '';
    document.getElementById('char-traits').value = (character.metadata?.personality_traits || []).join(', ');
    document.getElementById('char-background').value = character.metadata?.background || '';
    document.getElementById('char-content').value = character.content || '';

    // Reset portrait state
    selectedPortraitFile = null;
    document.getElementById('portrait-file').value = '';

    // Load existing portrait if any
    if (character.metadata?.portrait) {
        const preview = document.getElementById('portrait-preview');
        preview.src = apiUrl(`/characters/${characterId}/portrait`);
        preview.style.display = 'block';
        document.getElementById('portrait-placeholder').style.display = 'none';
        document.getElementById('remove-portrait-btn').style.display = 'block';
    } else {
        document.getElementById('portrait-preview').style.display = 'none';
        document.getElementById('portrait-placeholder').style.display = 'flex';
        document.getElementById('remove-portrait-btn').style.display = 'none';
    }

    // Show modal
    document.getElementById('character-modal').style.display = 'flex';
}

function renderWorlds() {
    const list = document.getElementById('worlds-list');

    if (worlds.length === 0) {
        list.innerHTML = '<div class="empty-state">No worlds yet. Create your first world context!</div>';
        return;
    }

    // Group by category
    const categoryLabels = {
        'locations': 'Locations',
        'lore': 'Lore & History',
        'factions': 'Factions & Groups',
        'systems': 'Systems & Rules',
        'other': 'Other'
    };

    const grouped = {};
    worlds.forEach(w => {
        const cat = w.metadata?.category || 'other';
        if (!grouped[cat]) grouped[cat] = [];
        grouped[cat].push(w);
    });

    // Render order
    const categoryOrder = ['locations', 'lore', 'factions', 'systems', 'other'];

    let html = '';
    categoryOrder.forEach(cat => {
        const items = grouped[cat];
        if (!items || items.length === 0) return;

        html += `
            <div class="world-category">
                <div class="world-category-header">${categoryLabels[cat]} (${items.length})</div>
                <div class="world-category-items">
                    ${items.map(w => `
                        <div class="item">
                            <div class="item-header">
                                <div class="item-title">${escapeHtml(w.metadata?.name || w.id)}</div>
                                <div class="item-actions">
                                    <button class="btn btn-small btn-danger" onclick="deleteWorld('${w.id}')">Delete</button>
                                </div>
                            </div>
                            <div class="item-meta">
                                ${w.metadata?.era ? `<span class="badge">${escapeHtml(w.metadata.era)}</span>` : ''}
                                ${w.metadata?.technology_level ? `<span class="badge">${escapeHtml(w.metadata.technology_level)}</span>` : ''}
                            </div>
                            ${w.content ? `<div class="item-content">${escapeHtml(w.content.substring(0, 150))}...</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });

    list.innerHTML = html;
}

function renderStructureTree() {
    const tree = document.getElementById('structure-tree');

    if (chapters.length === 0 && acts.length === 0) {
        tree.innerHTML = '<div class="empty-state">No structure yet. Create chapters to organize your scenes!</div>';
        return;
    }

    // Group chapters by act
    const actChapters = {};
    const noActChapters = [];

    chapters.forEach(ch => {
        if (ch.act_id) {
            if (!actChapters[ch.act_id]) actChapters[ch.act_id] = [];
            actChapters[ch.act_id].push(ch);
        } else {
            noActChapters.push(ch);
        }
    });

    let html = '';

    // Render acts with their chapters
    acts.forEach(act => {
        const actChapterList = actChapters[act.id] || [];
        html += `
            <div class="structure-act">
                <div class="structure-act-header">
                    <div class="structure-act-title">${escapeHtml(act.title)}</div>
                    <div class="item-actions">
                        <button class="btn btn-small" onclick="showReadingView('act', '${act.id}')">Read</button>
                        <button class="btn btn-small btn-danger" onclick="deleteAct('${act.id}')">Delete</button>
                    </div>
                </div>
                ${act.description ? `<p class="text-muted">${escapeHtml(act.description)}</p>` : ''}
                <div class="structure-chapters">
                    ${actChapterList.map(ch => renderStructureChapter(ch)).join('')}
                </div>
            </div>
        `;
    });

    // Render chapters without acts
    if (noActChapters.length > 0) {
        html += `
            <div class="structure-chapters">
                ${noActChapters.map(ch => renderStructureChapter(ch)).join('')}
            </div>
        `;
    }

    tree.innerHTML = html;
}

function renderStructureChapter(chapter) {
    const chapterScenes = scenes.filter(s => s.chapter_id === chapter.id);
    chapterScenes.sort((a, b) => (a.scene_number || 0) - (b.scene_number || 0));
    const canonCount = chapterScenes.filter(s => s.is_canon).length;

    return `
        <div class="structure-chapter">
            <div class="structure-chapter-header">
                <div class="structure-chapter-title">Chapter ${chapter.chapter_number}: ${escapeHtml(chapter.title)}</div>
                <div class="item-actions">
                    <button class="btn btn-small" onclick="showReadingView('chapter', '${chapter.id}')">Read</button>
                    <button class="btn btn-small" onclick="showSceneFormForChapter('${chapter.id}')">+ Scene</button>
                    <button class="btn btn-small btn-danger" onclick="deleteChapter('${chapter.id}')">Delete</button>
                </div>
            </div>
            <div class="structure-chapter-meta">
                <span class="badge">${chapterScenes.length} scenes</span>
                ${canonCount > 0 ? `<span class="badge canon">${canonCount} canon</span>` : ''}
                ${chapter.word_count > 0 ? `<span class="badge">${chapter.word_count.toLocaleString()} words</span>` : ''}
            </div>
            ${chapter.description ? `<p class="text-muted" style="font-size: 0.9rem;">${escapeHtml(chapter.description)}</p>` : ''}
            <div class="structure-scenes">
                ${chapterScenes.map(s => {
                    const isEditMode = s.edit_mode;
                    const badges = [];
                    if (s.is_canon) badges.push('<span class="badge canon">Canon</span>');
                    if (isEditMode) badges.push('<span class="badge edit-mode">Edit Mode</span>');

                    // Show import button for non-canon scenes without edit mode
                    const importBtn = !s.is_canon && !isEditMode
                        ? `<button class="btn btn-small" onclick="event.stopPropagation(); showImportProseModal('${s.id}')" title="Import existing prose for revision">Import</button>`
                        : '';

                    // Show start edit generation for scenes in edit mode
                    const editGenBtn = isEditMode && !s.is_canon
                        ? `<button class="btn btn-small btn-success" onclick="event.stopPropagation(); startEditModeGeneration('${s.id}')" title="Start critique and revision">Revise</button>`
                        : '';

                    return `
                        <div class="structure-scene ${s.is_canon ? 'canon' : ''} ${isEditMode ? 'edit-mode' : ''}" onclick="showReadingView('scene', '${s.id}')">
                            <span>${escapeHtml(s.title)}</span>
                            <div class="item-actions">
                                ${badges.join('')}
                                ${importBtn}
                                ${editGenBtn}
                                <button class="btn btn-small btn-danger" onclick="event.stopPropagation(); deleteScene('${s.id}')">Delete</button>
                            </div>
                        </div>
                    `;
                }).join('')}
                ${chapterScenes.length === 0 ? '<div class="empty-state" style="padding: 10px;">No scenes yet</div>' : ''}
            </div>
        </div>
    `;
}

// ============================================
// Act CRUD
// ============================================
function showActForm() {
    document.getElementById('act-form').style.display = 'block';
    document.getElementById('act-title').focus();
    navigateToView('structure');
}

function hideActForm() {
    document.getElementById('act-form').style.display = 'none';
    document.getElementById('act-title').value = '';
    document.getElementById('act-description').value = '';
}

async function saveAct(e) {
    e.preventDefault();

    const title = document.getElementById('act-title').value.trim();
    const description = document.getElementById('act-description').value.trim();

    if (!title) {
        alert('Please enter an act title');
        return;
    }

    try {
        const response = await fetch(apiUrl('/acts/'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description: description || undefined })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create act');
        }

        hideActForm();
        await loadActs();
        populateFormSelects();
        renderOutlineTree();
        renderStructureTree();
    } catch (e) {
        alert('Error creating act: ' + e.message);
    }
}

async function deleteAct(actId) {
    if (!confirm('Delete this act? Chapters will be unassigned but not deleted.')) return;

    try {
        await fetch(apiUrl(`/acts/${actId}`), { method: 'DELETE' });
        await loadActs();
        await loadChapters();
        populateFormSelects();
        renderOutlineTree();
        renderStructureTree();
    } catch (e) {
        alert('Error deleting act: ' + e.message);
    }
}

// ============================================
// Chapter CRUD
// ============================================
function showChapterForm() {
    document.getElementById('chapter-form').style.display = 'block';
    document.getElementById('chapter-title').focus();
    navigateToView('structure');
}

function hideChapterForm() {
    document.getElementById('chapter-form').style.display = 'none';
    document.getElementById('chapter-title').value = '';
    document.getElementById('chapter-description').value = '';
    document.getElementById('chapter-act').value = '';
    document.getElementById('chapter-notes').value = '';
}

async function saveChapter(e) {
    e.preventDefault();

    const title = document.getElementById('chapter-title').value.trim();
    const description = document.getElementById('chapter-description').value.trim();
    const actId = document.getElementById('chapter-act').value;
    const notes = document.getElementById('chapter-notes').value.trim();

    if (!title) {
        alert('Please enter a chapter title');
        return;
    }

    try {
        const response = await fetch(apiUrl('/chapters/'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title,
                description: description || undefined,
                act_id: actId || undefined,
                notes: notes || undefined
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create chapter');
        }

        hideChapterForm();
        await loadChapters();
        updateStats();
        populateFormSelects();
        renderOutlineTree();
        renderStructureTree();
    } catch (e) {
        alert('Error creating chapter: ' + e.message);
    }
}

async function deleteChapter(chapterId) {
    const chapterScenes = scenes.filter(s => s.chapter_id === chapterId);
    if (chapterScenes.length > 0) {
        alert(`Cannot delete chapter with ${chapterScenes.length} scene(s). Delete or move scenes first.`);
        return;
    }

    if (!confirm('Delete this chapter?')) return;

    try {
        await fetch(apiUrl(`/chapters/${chapterId}`), { method: 'DELETE' });
        await loadChapters();
        updateStats();
        populateFormSelects();
        renderOutlineTree();
        renderStructureTree();
    } catch (e) {
        alert('Error deleting chapter: ' + e.message);
    }
}

// ============================================
// Character CRUD
// ============================================
let selectedPortraitFile = null;
let editingCharacterId = null;

function showCharacterForm(characterId = null) {
    editingCharacterId = characterId;
    document.getElementById('character-modal').style.display = 'flex';
    document.getElementById('character-form-title').textContent = characterId ? 'Edit Character' : 'New Character';

    // Reset portrait
    selectedPortraitFile = null;
    document.getElementById('portrait-preview').style.display = 'none';
    document.getElementById('portrait-placeholder').style.display = 'flex';
    document.getElementById('remove-portrait-btn').style.display = 'none';
    document.getElementById('portrait-file').value = '';

    document.getElementById('char-name').focus();
}

function hideCharacterForm() {
    document.getElementById('character-modal').style.display = 'none';
    document.getElementById('char-name').value = '';
    document.getElementById('char-role').value = '';
    document.getElementById('char-age').value = '';
    document.getElementById('char-occupation').value = '';
    document.getElementById('char-traits').value = '';
    document.getElementById('char-background').value = '';
    document.getElementById('char-content').value = '';

    // Reset portrait
    selectedPortraitFile = null;
    editingCharacterId = null;
    document.getElementById('portrait-preview').style.display = 'none';
    document.getElementById('portrait-preview').src = '';
    document.getElementById('portrait-placeholder').style.display = 'flex';
    document.getElementById('remove-portrait-btn').style.display = 'none';
    document.getElementById('portrait-file').value = '';
}

function handlePortraitSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        alert('Please select a valid image file (JPEG, PNG, GIF, or WebP)');
        return;
    }

    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
        alert('Image too large. Maximum size is 5MB.');
        return;
    }

    selectedPortraitFile = file;

    // Show preview
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('portrait-preview');
        preview.src = e.target.result;
        preview.style.display = 'block';
        document.getElementById('portrait-placeholder').style.display = 'none';
        document.getElementById('remove-portrait-btn').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

async function removePortrait() {
    // If editing existing character with a portrait, delete from server
    if (editingCharacterId) {
        const character = characters.find(c => c.id === editingCharacterId);
        if (character?.metadata?.portrait) {
            try {
                await fetch(apiUrl(`/characters/${editingCharacterId}/portrait`), {
                    method: 'DELETE'
                });
            } catch (e) {
                console.error('Failed to delete portrait:', e);
            }
        }
    }

    selectedPortraitFile = null;
    document.getElementById('portrait-preview').style.display = 'none';
    document.getElementById('portrait-preview').src = '';
    document.getElementById('portrait-placeholder').style.display = 'flex';
    document.getElementById('remove-portrait-btn').style.display = 'none';
    document.getElementById('portrait-file').value = '';
}

async function uploadPortrait(characterId) {
    if (!selectedPortraitFile) return;

    const formData = new FormData();
    formData.append('file', selectedPortraitFile);

    try {
        const response = await fetch(apiUrl(`/characters/${characterId}/portrait`), {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            console.error('Portrait upload failed:', error.detail);
        }
    } catch (e) {
        console.error('Portrait upload error:', e);
    }
}

async function saveCharacter(e) {
    e.preventDefault();

    const name = document.getElementById('char-name').value.trim();
    const role = document.getElementById('char-role').value.trim();
    const age = document.getElementById('char-age').value;
    const occupation = document.getElementById('char-occupation').value.trim();
    const traits = document.getElementById('char-traits').value.trim();
    const background = document.getElementById('char-background').value.trim();
    const content = document.getElementById('char-content').value.trim();

    const metadata = {
        name,
        role: role || undefined,
        age: age ? parseInt(age) : undefined,
        occupation: occupation || undefined,
        personality_traits: traits ? traits.split(',').map(t => t.trim()) : [],
        background: background || undefined
    };

    try {
        let characterId;

        if (editingCharacterId) {
            // Update existing character
            const response = await fetch(apiUrl(`/characters/${editingCharacterId}`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ metadata, content })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update character');
            }

            characterId = editingCharacterId;
        } else {
            // Create new character
            const filename = name.toLowerCase().replace(/[^a-z0-9]+/g, '-') + '.md';
            const response = await fetch(apiUrl('/characters/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, metadata, content })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create character');
            }

            const character = await response.json();
            characterId = character.id;
        }

        // Upload portrait if selected
        if (selectedPortraitFile) {
            await uploadPortrait(characterId);
        }

        hideCharacterForm();
        await loadCharacters();
        updateStats();
        populateFormSelects();
    } catch (e) {
        alert('Error creating character: ' + e.message);
    }
}

async function deleteCharacter(characterId) {
    if (!confirm('Delete this character?')) return;

    try {
        await fetch(apiUrl(`/characters/${characterId}`), { method: 'DELETE' });
        await loadCharacters();
        updateStats();
        populateFormSelects();
    } catch (e) {
        alert('Error deleting character: ' + e.message);
    }
}

// ============================================
// World CRUD
// ============================================
function showWorldForm() {
    document.getElementById('world-form').style.display = 'block';
    document.getElementById('world-name').focus();
}

function hideWorldForm() {
    document.getElementById('world-form').style.display = 'none';
    document.getElementById('world-name').value = '';
    document.getElementById('world-category').value = 'locations';
    document.getElementById('world-era').value = '';
    document.getElementById('world-tech').value = '';
    document.getElementById('world-magic').value = '';
    document.getElementById('world-content').value = '';
}

async function saveWorld(e) {
    e.preventDefault();

    const name = document.getElementById('world-name').value.trim();
    const category = document.getElementById('world-category').value;
    const era = document.getElementById('world-era').value.trim();
    const tech = document.getElementById('world-tech').value.trim();
    const magic = document.getElementById('world-magic').value.trim();
    const content = document.getElementById('world-content').value.trim();

    const filename = name.toLowerCase().replace(/[^a-z0-9]+/g, '-') + '.md';

    const metadata = {
        name,
        category,
        era: era || undefined,
        technology_level: tech || undefined,
        magic_system: magic || undefined
    };

    try {
        const response = await fetch(apiUrl('/world/'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename, metadata, content })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create world');
        }

        hideWorldForm();
        await loadWorlds();
        updateStats();
        populateFormSelects();
    } catch (e) {
        alert('Error creating world: ' + e.message);
    }
}

async function deleteWorld(worldId) {
    if (!confirm('Delete this world context?')) return;

    try {
        await fetch(apiUrl(`/world/${worldId}`), { method: 'DELETE' });
        await loadWorlds();
        updateStats();
        populateFormSelects();
    } catch (e) {
        alert('Error deleting world: ' + e.message);
    }
}

// ============================================
// Scene CRUD
// ============================================
function showSceneForm() {
    document.getElementById('scene-form').style.display = 'block';
    document.getElementById('scene-chapter').focus();
    navigateToView('structure');
}

function showSceneFormForChapter(chapterId) {
    showSceneForm();
    document.getElementById('scene-chapter').value = chapterId;
    document.getElementById('scene-title').focus();
}

function hideSceneForm() {
    document.getElementById('scene-form').style.display = 'none';
    document.getElementById('scene-chapter').value = '';
    document.getElementById('scene-title').value = '';
    document.getElementById('scene-outline').value = '';
    document.getElementById('scene-tone').value = '';
    document.getElementById('scene-pov').value = '';
    document.getElementById('scene-length').value = '';
    document.getElementById('scene-number').value = '';
    document.getElementById('scene-characters').selectedIndex = -1;
    document.getElementById('scene-world').value = '';
    document.getElementById('scene-previous').selectedIndex = -1;
    document.getElementById('scene-notes').value = '';
}

async function saveScene(e) {
    e.preventDefault();

    const chapterId = document.getElementById('scene-chapter').value;
    const title = document.getElementById('scene-title').value.trim();
    const outline = document.getElementById('scene-outline').value.trim();
    const tone = document.getElementById('scene-tone').value.trim();
    const pov = document.getElementById('scene-pov').value.trim();
    const targetLength = document.getElementById('scene-length').value.trim();
    const sceneNumber = document.getElementById('scene-number').value;
    const notes = document.getElementById('scene-notes').value.trim();

    if (!chapterId) {
        alert('Please select a chapter');
        return;
    }

    // Get selected characters
    const charSelect = document.getElementById('scene-characters');
    const characterIds = Array.from(charSelect.selectedOptions).map(o => o.value);

    // Get selected world
    const worldSelect = document.getElementById('scene-world');
    const worldContextIds = worldSelect.value ? [worldSelect.value] : [];

    // Get previous scenes
    const prevSelect = document.getElementById('scene-previous');
    const previousSceneIds = Array.from(prevSelect.selectedOptions).map(o => o.value);

    try {
        const response = await fetch(apiUrl('/scenes/'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chapter_id: chapterId,
                title,
                outline,
                tone: tone || undefined,
                pov: pov || undefined,
                target_length: targetLength || undefined,
                scene_number: sceneNumber ? parseInt(sceneNumber) : undefined,
                character_ids: characterIds,
                world_context_ids: worldContextIds,
                previous_scene_ids: previousSceneIds,
                additional_notes: notes || undefined
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create scene');
        }

        hideSceneForm();
        await loadScenes();
        await loadChapters(); // Refresh chapter stats
        updateStats();
        populateFormSelects();
        renderOutlineTree();
        renderStructureTree();
    } catch (e) {
        alert('Error creating scene: ' + e.message);
    }
}

async function deleteScene(sceneId) {
    if (!confirm('Delete this scene?')) return;

    try {
        await fetch(apiUrl(`/scenes/${sceneId}`), { method: 'DELETE' });
        await loadScenes();
        await loadChapters();
        updateStats();
        populateFormSelects();
        renderOutlineTree();
        renderStructureTree();
    } catch (e) {
        alert('Error deleting scene: ' + e.message);
    }
}

// ============================================
// Reading View
// ============================================
async function showReadingView(type, id) {
    // Save current view to return to
    const activeNav = document.querySelector('.nav-btn.active');
    if (activeNav) {
        previousView = activeNav.dataset.view;
    }

    let title = '';
    let subtitle = '';
    let prose = '';
    let wordCount = 0;

    try {
        if (type === 'scene') {
            const response = await fetch(apiUrl(`/scenes/${id}/prose`));
            const data = await response.json();

            title = data.title;
            subtitle = data.is_canon ? 'Canon Scene' : 'Not yet canon';
            prose = data.prose || '';
            wordCount = data.word_count || 0;

            currentReadingData = { type, id, title, prose, is_canon: data.is_canon };
            document.getElementById('reference-btn').style.display = 'inline-flex';
            document.getElementById('edit-prose-btn').style.display = 'inline-flex';

        } else if (type === 'chapter') {
            const response = await fetch(apiUrl(`/chapters/${id}/prose`));
            const data = await response.json();

            title = `Chapter ${data.chapter_number}: ${data.chapter_title}`;
            subtitle = `${data.scene_count} canon scenes`;
            prose = data.prose || 'No canon scenes in this chapter yet.';
            wordCount = data.word_count || 0;

            currentReadingData = { type, id, title, prose };
            document.getElementById('reference-btn').style.display = 'inline-flex';
            document.getElementById('edit-prose-btn').style.display = 'none';

        } else if (type === 'manuscript') {
            title = currentProject.title;
            subtitle = 'Full Manuscript';

            // Collect all canon prose in order
            const proseBlocks = [];
            chapters.sort((a, b) => a.chapter_number - b.chapter_number);

            for (const chapter of chapters) {
                const chapterScenes = scenes.filter(s => s.chapter_id === chapter.id && s.is_canon);
                chapterScenes.sort((a, b) => (a.scene_number || 0) - (b.scene_number || 0));

                if (chapterScenes.length > 0) {
                    proseBlocks.push(`\n\n## Chapter ${chapter.chapter_number}: ${chapter.title}\n\n`);
                    for (const scene of chapterScenes) {
                        if (scene.prose) {
                            proseBlocks.push(scene.prose);
                            proseBlocks.push('\n\n---\n\n');
                            wordCount += scene.prose.split(/\s+/).length;
                        }
                    }
                }
            }

            prose = proseBlocks.join('') || 'No canon content yet. Generate and accept scenes to build your manuscript.';
            currentReadingData = { type, id: null, title, prose };
            document.getElementById('reference-btn').style.display = 'none';
            document.getElementById('edit-prose-btn').style.display = 'none';

        } else if (type === 'act') {
            const act = acts.find(a => a.id === id);
            if (!act) throw new Error('Act not found');

            title = act.title;
            const actChapters = chapters.filter(ch => ch.act_id === id);
            subtitle = `${actChapters.length} chapters`;

            // Collect all canon prose from chapters in this act
            const proseBlocks = [];
            actChapters.sort((a, b) => a.chapter_number - b.chapter_number);

            for (const chapter of actChapters) {
                const chapterScenes = scenes.filter(s => s.chapter_id === chapter.id && s.is_canon);
                chapterScenes.sort((a, b) => (a.scene_number || 0) - (b.scene_number || 0));

                if (chapterScenes.length > 0) {
                    proseBlocks.push(`\n\n### Chapter ${chapter.chapter_number}: ${chapter.title}\n\n`);
                    for (const scene of chapterScenes) {
                        if (scene.prose) {
                            proseBlocks.push(scene.prose);
                            proseBlocks.push('\n\n---\n\n');
                            wordCount += scene.prose.split(/\s+/).length;
                        }
                    }
                }
            }

            prose = proseBlocks.join('') || 'No canon content in this act yet.';
            currentReadingData = { type, id, title, prose };
            document.getElementById('reference-btn').style.display = 'inline-flex';
            document.getElementById('edit-prose-btn').style.display = 'none';
        }

    } catch (e) {
        console.error('Error loading reading view:', e);
        prose = 'Error loading content: ' + e.message;
    }

    document.getElementById('reading-title').textContent = title;
    document.getElementById('reading-subtitle').textContent = subtitle;
    document.getElementById('reading-content').textContent = prose || 'No prose yet. Click "Edit Prose" to write or generate this scene.';
    document.getElementById('reading-stats').textContent = wordCount > 0 ? `${wordCount.toLocaleString()} words` : '';

    // Make sure we're in reading mode, not editing mode
    document.getElementById('reading-mode').style.display = 'block';
    document.getElementById('editing-mode').style.display = 'none';

    // Show reading view
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.main-content .view').forEach(v => v.classList.remove('active'));
    document.getElementById('reading-view').classList.add('active');
}

function closeReadingView() {
    // Check if we're in edit mode with unsaved changes
    const editingMode = document.getElementById('editing-mode');
    if (editingMode && editingMode.style.display !== 'none' && hasUnsavedChanges) {
        if (!confirm('You have unsaved changes. Are you sure you want to leave?')) {
            return;
        }
        cleanupProseEditor();
    }

    const viewToShow = previousView || 'dashboard';
    navigateToView(viewToShow);
    currentReadingData = null;
}

// Warn before closing browser tab with unsaved changes
window.addEventListener('beforeunload', (e) => {
    if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
        return '';
    }
});

// ============================================
// Prose Editing
// ============================================
let autoSaveTimeout = null;
let lastSavedProse = '';
let lastSavedCanon = false;
let hasUnsavedChanges = false;

function startEditingProse() {
    if (!currentReadingData || currentReadingData.type !== 'scene') return;

    // Switch to editing mode
    document.getElementById('reading-mode').style.display = 'none';
    document.getElementById('editing-mode').style.display = 'block';

    // Populate editor
    const editor = document.getElementById('prose-editor');
    editor.value = currentReadingData.prose || '';

    // Set canon checkbox
    document.getElementById('mark-as-canon').checked = currentReadingData.is_canon || false;

    // Track last saved state
    lastSavedProse = editor.value;
    lastSavedCanon = currentReadingData.is_canon || false;
    hasUnsavedChanges = false;
    updateSaveStatus('saved');

    // Update word count
    updateEditingWordCount();

    // Add listeners
    editor.addEventListener('input', onProseEditorInput);
    document.getElementById('mark-as-canon').addEventListener('change', onCanonCheckboxChange);

    // Hide edit button while editing
    document.getElementById('edit-prose-btn').style.display = 'none';
}

function onProseEditorInput() {
    updateEditingWordCount();
    checkForUnsavedChanges();
    scheduleAutoSave();
}

function onCanonCheckboxChange() {
    checkForUnsavedChanges();
    scheduleAutoSave();
}

function checkForUnsavedChanges() {
    const currentProse = document.getElementById('prose-editor').value;
    const currentCanon = document.getElementById('mark-as-canon').checked;
    hasUnsavedChanges = (currentProse !== lastSavedProse) || (currentCanon !== lastSavedCanon);

    if (hasUnsavedChanges) {
        updateSaveStatus('unsaved');
    }
}

function scheduleAutoSave() {
    // Clear existing timeout
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }

    // Schedule save after 2 seconds of no typing
    autoSaveTimeout = setTimeout(async () => {
        if (hasUnsavedChanges) {
            await autoSaveProse();
        }
    }, 2000);
}

function updateSaveStatus(status) {
    const statusEl = document.getElementById('editing-word-count');
    const wordCount = statusEl.textContent.split(' ')[0]; // Keep word count

    switch (status) {
        case 'saving':
            statusEl.innerHTML = `${wordCount} words &nbsp;|&nbsp; <span style="color: var(--warning);">Saving...</span>`;
            break;
        case 'saved':
            statusEl.innerHTML = `${wordCount} words &nbsp;|&nbsp; <span style="color: var(--success);">Saved</span>`;
            break;
        case 'unsaved':
            statusEl.innerHTML = `${wordCount} words &nbsp;|&nbsp; <span style="color: var(--text-muted);">Unsaved changes</span>`;
            break;
        case 'error':
            statusEl.innerHTML = `${wordCount} words &nbsp;|&nbsp; <span style="color: var(--danger);">Save failed</span>`;
            break;
    }
}

async function autoSaveProse() {
    if (!currentReadingData || currentReadingData.type !== 'scene') return;

    const prose = document.getElementById('prose-editor').value;
    const isCanon = document.getElementById('mark-as-canon').checked;

    updateSaveStatus('saving');

    try {
        const response = await fetch(apiUrl(`/scenes/${currentReadingData.id}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prose: prose || null,
                is_canon: isCanon
            })
        });

        if (!response.ok) {
            throw new Error('Failed to save');
        }

        // Update tracking
        lastSavedProse = prose;
        lastSavedCanon = isCanon;
        hasUnsavedChanges = false;

        // Update current data
        currentReadingData.prose = prose;
        currentReadingData.is_canon = isCanon;

        updateSaveStatus('saved');

    } catch (e) {
        console.error('Auto-save failed:', e);
        updateSaveStatus('error');
    }
}

function updateEditingWordCount() {
    const editor = document.getElementById('prose-editor');
    const text = editor.value.trim();
    const wordCount = text ? text.split(/\s+/).length : 0;
    document.getElementById('editing-word-count').textContent = `${wordCount.toLocaleString()} words`;
}

function cancelProseEdit() {
    // Check for unsaved changes
    if (hasUnsavedChanges) {
        if (!confirm('You have unsaved changes. Are you sure you want to discard them?')) {
            return;
        }
    }

    // Clean up
    cleanupProseEditor();

    // Switch back to reading mode
    document.getElementById('editing-mode').style.display = 'none';
    document.getElementById('reading-mode').style.display = 'block';

    // Show edit button again
    document.getElementById('edit-prose-btn').style.display = 'inline-flex';
}

function cleanupProseEditor() {
    // Clear auto-save timeout
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
        autoSaveTimeout = null;
    }

    // Remove event listeners
    const editor = document.getElementById('prose-editor');
    editor.removeEventListener('input', onProseEditorInput);
    document.getElementById('mark-as-canon').removeEventListener('change', onCanonCheckboxChange);

    // Reset state
    hasUnsavedChanges = false;
}

async function saveProseEdit() {
    if (!currentReadingData || currentReadingData.type !== 'scene') return;

    const prose = document.getElementById('prose-editor').value;
    const isCanon = document.getElementById('mark-as-canon').checked;

    updateSaveStatus('saving');

    try {
        const response = await fetch(apiUrl(`/scenes/${currentReadingData.id}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prose: prose || null,
                is_canon: isCanon
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save');
        }

        // Update tracking
        lastSavedProse = prose;
        lastSavedCanon = isCanon;
        hasUnsavedChanges = false;

        // Update current data
        currentReadingData.prose = prose;
        currentReadingData.is_canon = isCanon;

        // Update reading view content
        document.getElementById('reading-content').textContent = prose || 'No prose yet. Click "Edit Prose" to write or generate this scene.';

        // Update subtitle
        document.getElementById('reading-subtitle').textContent = isCanon ? 'Canon Scene' : 'Not yet canon';

        // Update word count
        const wordCount = prose ? prose.trim().split(/\s+/).length : 0;
        document.getElementById('reading-stats').textContent = wordCount > 0 ? `${wordCount.toLocaleString()} words` : '';

        // Clean up editor
        cleanupProseEditor();

        // Switch back to reading mode
        document.getElementById('editing-mode').style.display = 'none';
        document.getElementById('reading-mode').style.display = 'block';
        document.getElementById('edit-prose-btn').style.display = 'inline-flex';

        // Refresh data to update stats
        await loadScenes();
        await loadChapters();
        updateStats();
        renderOutlineTree();
        renderStructureTree();

    } catch (e) {
        updateSaveStatus('error');
        alert('Error saving prose: ' + e.message);
    }
}

// ============================================
// Reference Panel
// ============================================
function openReferencePanel() {
    if (!currentReadingData) return;

    document.getElementById('reference-title').textContent = currentReadingData.title;
    document.getElementById('reference-content').textContent = currentReadingData.prose;
    document.getElementById('reference-panel').style.display = 'block';

    // Go back to previous view but keep reference open
    closeReadingView();
}

function closeReferencePanel() {
    document.getElementById('reference-panel').style.display = 'none';
}

// ============================================
// Generation Pipeline
// ============================================
function onSceneSelected() {
    const select = document.getElementById('gen-scene-select');
    const preview = document.getElementById('gen-scene-preview');
    const startBtn = document.getElementById('gen-start-btn');

    if (select.value) {
        const scene = scenes.find(s => s.id === select.value);
        if (scene) {
            document.getElementById('gen-preview-title').textContent = scene.title;
            document.getElementById('gen-preview-outline').textContent = scene.outline;
            preview.style.display = 'block';
            startBtn.disabled = false;
        }
    } else {
        preview.style.display = 'none';
        startBtn.disabled = true;
    }
}

async function startGeneration() {
    const sceneId = document.getElementById('gen-scene-select').value;
    const genModel = document.getElementById('gen-model').value || undefined;
    const critiqueModel = document.getElementById('critique-model').value || undefined;

    if (!sceneId) {
        alert('Please select a scene');
        return;
    }

    // Validate models are different if both specified
    if (genModel && critiqueModel && genModel === critiqueModel) {
        alert('Generation and Critique models must be different for effective revision feedback.');
        return;
    }

    // Store models for display
    currentGenModel = genModel || 'Default';
    currentCritiqueModel = critiqueModel || 'Default';

    try {
        // Show progress step
        document.getElementById('gen-step-select').style.display = 'none';
        document.getElementById('gen-step-progress').style.display = 'block';
        updateProgress('initialized', 'Starting generation...');

        const response = await fetch(apiUrl('/generations/start'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scene_id: sceneId,
                max_iterations: 99,
                generation_model: genModel,
                critique_model: critiqueModel
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start generation');
        }

        const data = await response.json();
        currentGenId = data.generation_id;

        // Start polling
        startPolling();

    } catch (e) {
        alert('Error starting generation: ' + e.message);
        resetGeneration();
    }
}

function startPolling() {
    pollingInterval = setInterval(checkGenerationProgress, 2000);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

async function checkGenerationProgress() {
    if (!currentGenId) return;

    try {
        const response = await fetch(apiUrl(`/generations/${currentGenId}`));
        const data = await response.json();

        updateProgress(data.status, getStatusMessage(data.status));

        if (data.status === 'awaiting_approval') {
            stopPolling();
            showReviewStep(data);
        } else if (data.status === 'completed') {
            stopPolling();
            showCompleteStep(data);
        } else if (data.status === 'error') {
            stopPolling();
            alert('Generation error: ' + (data.error_message || 'Unknown error'));
            resetGeneration();
        } else if (data.status === 'rejected') {
            stopPolling();
            resetGeneration();
        }
    } catch (e) {
        console.error('Error checking progress:', e);
    }
}

function updateProgress(status, message) {
    const statusEl = document.getElementById('gen-status');
    const detailEl = document.getElementById('gen-status-detail');
    const fillEl = document.getElementById('gen-progress-fill');

    statusEl.textContent = message;
    detailEl.textContent = getStatusDetail(status);

    // Update progress bar
    const progressMap = {
        'initialized': 10,
        'generating': 30,
        'generation_complete': 50,
        'critiquing': 70,
        'awaiting_approval': 90,
        'revising': 50,
        'generating_summary': 95,
        'completed': 100
    };
    fillEl.style.width = (progressMap[status] || 10) + '%';
}

function getStatusMessage(status) {
    const messages = {
        'initialized': 'Initializing...',
        'generating': 'Generating prose...',
        'generation_complete': 'Generation complete',
        'critiquing': 'Running AI critique...',
        'awaiting_approval': 'Ready for review',
        'revising': 'Revising based on critique...',
        'generating_summary': 'Generating summary...',
        'completed': 'Complete!'
    };
    return messages[status] || status;
}

function getStatusDetail(status) {
    const details = {
        'initialized': 'Setting up generation pipeline...',
        'generating': 'Claude is writing prose based on your scene outline...',
        'generation_complete': 'Prose generated, preparing critique...',
        'critiquing': 'Claude is analyzing the prose for improvements...',
        'awaiting_approval': 'Review the prose and critique below',
        'revising': 'Incorporating feedback into revised prose...',
        'generating_summary': 'Creating a summary for continuity...',
        'completed': 'Scene saved as canon!'
    };
    return details[status] || '';
}

function showReviewStep(data) {
    document.getElementById('gen-step-progress').style.display = 'none';
    document.getElementById('gen-step-review').style.display = 'block';

    document.getElementById('gen-iteration').textContent = data.current_iteration;
    document.getElementById('gen-prose').textContent = data.current_prose || '';
    document.getElementById('gen-critique').textContent = data.current_critique || '';

    // Show word count
    const prose = data.current_prose || '';
    const wordCount = prose.trim() ? prose.trim().split(/\s+/).length : 0;
    document.getElementById('gen-prose-word-count').textContent = `${wordCount.toLocaleString()} words`;

    // Show models used
    const genModelDisplay = currentGenModel === 'Default' ? 'Default' : currentGenModel.split('/').pop();
    const critiqueModelDisplay = currentCritiqueModel === 'Default' ? 'Default' : currentCritiqueModel.split('/').pop();
    document.getElementById('gen-model-used').textContent = `(${genModelDisplay})`;
    document.getElementById('critique-model-used').textContent = `(${critiqueModelDisplay})`;

    // Revise button always enabled (user controls when to stop)
    const reviseBtn = document.getElementById('gen-revise-btn');
    reviseBtn.disabled = false;
    reviseBtn.textContent = 'Approve & Revise';
}

function showCompleteStep(data) {
    document.getElementById('gen-step-progress').style.display = 'none';
    document.getElementById('gen-step-review').style.display = 'none';
    document.getElementById('gen-step-complete').style.display = 'block';

    document.getElementById('gen-summary').textContent = data.scene_summary || 'Summary not generated';
}

async function approveAndRevise() {
    if (!currentGenId) return;

    try {
        document.getElementById('gen-step-review').style.display = 'none';
        document.getElementById('gen-step-progress').style.display = 'block';
        updateProgress('revising', 'Revising based on critique...');

        const response = await fetch(apiUrl(`/generations/${currentGenId}/approve`), {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to approve');
        }

        startPolling();
    } catch (e) {
        alert('Error: ' + e.message);
        document.getElementById('gen-step-progress').style.display = 'none';
        document.getElementById('gen-step-review').style.display = 'block';
    }
}

async function acceptFinal() {
    if (!currentGenId) return;

    try {
        document.getElementById('gen-step-review').style.display = 'none';
        document.getElementById('gen-step-progress').style.display = 'block';
        updateProgress('generating_summary', 'Generating summary...');

        const response = await fetch(apiUrl(`/generations/${currentGenId}/accept`), {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to accept');
        }

        startPolling();
    } catch (e) {
        alert('Error: ' + e.message);
        document.getElementById('gen-step-progress').style.display = 'none';
        document.getElementById('gen-step-review').style.display = 'block';
    }
}

async function rejectGeneration() {
    if (!currentGenId) return;

    if (!confirm('Reject this generation and start over?')) return;

    try {
        await fetch(apiUrl(`/generations/${currentGenId}/reject`), {
            method: 'POST'
        });
    } catch (e) {
        console.error('Error rejecting:', e);
    }

    resetGeneration();
}

function resetGeneration() {
    stopPolling();
    currentGenId = null;

    document.getElementById('gen-step-select').style.display = 'block';
    document.getElementById('gen-step-progress').style.display = 'none';
    document.getElementById('gen-step-review').style.display = 'none';
    document.getElementById('gen-step-complete').style.display = 'none';

    document.getElementById('gen-scene-select').value = '';
    document.getElementById('gen-scene-preview').style.display = 'none';
    document.getElementById('gen-start-btn').disabled = true;

    // Reload data to update canon status
    loadScenes().then(() => {
        loadChapters().then(() => {
            updateStats();
            populateFormSelects();
            renderOutlineTree();
            renderStructureTree();
        });
    });
}

// ============================================
// Chat Functions
// ============================================
function populateChatScopeSelect() {
    const select = document.getElementById('chat-scope-select');
    if (!select) return;

    let html = '<option value="">-- Select Scope --</option>';
    html += '<option value="project">Project-wide</option>';

    // Add chapters
    if (chapters.length > 0) {
        html += '<optgroup label="Chapters">';
        chapters.forEach(ch => {
            html += `<option value="chapter:${ch.id}">Ch ${ch.chapter_number}: ${escapeHtml(ch.title)}</option>`;
        });
        html += '</optgroup>';
    }

    // Add canon scenes
    const canonScenes = scenes.filter(s => s.is_canon);
    if (canonScenes.length > 0) {
        html += '<optgroup label="Scenes">';
        canonScenes.forEach(s => {
            const chapter = chapters.find(ch => ch.id === s.chapter_id);
            const prefix = chapter ? `Ch ${chapter.chapter_number}: ` : '';
            html += `<option value="scene:${s.id}">${prefix}${escapeHtml(s.title)}</option>`;
        });
        html += '</optgroup>';
    }

    select.innerHTML = html;
}

async function onChatScopeChange() {
    const select = document.getElementById('chat-scope-select');
    const value = select.value;

    if (!value) {
        currentChatScope = null;
        currentChatScopeId = null;
        currentConversation = null;
        renderChatEmpty();
        document.getElementById('chat-input-container').style.display = 'none';
        return;
    }

    // Parse scope value
    if (value === 'project') {
        currentChatScope = 'project';
        currentChatScopeId = null;
    } else if (value.startsWith('chapter:')) {
        currentChatScope = 'chapter';
        currentChatScopeId = value.substring(8);
    } else if (value.startsWith('scene:')) {
        currentChatScope = 'scene';
        currentChatScopeId = value.substring(6);
    }

    // Update scope info text
    updateChatScopeInfo();

    // Load existing conversation
    await loadChatConversation();

    // Show input
    document.getElementById('chat-input-container').style.display = 'block';
    document.getElementById('chat-input').focus();

    // Enable send button based on input
    updateChatSendButton();
}

function updateChatScopeInfo() {
    const infoEl = document.getElementById('chat-scope-info');
    let scopeText = '';

    if (currentChatScope === 'project') {
        scopeText = 'Chatting about the entire project';
    } else if (currentChatScope === 'chapter' && currentChatScopeId) {
        const chapter = chapters.find(ch => ch.id === currentChatScopeId);
        scopeText = chapter ? `Chatting about Chapter ${chapter.chapter_number}: ${chapter.title}` : 'Chapter chat';
    } else if (currentChatScope === 'scene' && currentChatScopeId) {
        const scene = scenes.find(s => s.id === currentChatScopeId);
        scopeText = scene ? `Chatting about scene: ${scene.title}` : 'Scene chat';
    }

    infoEl.textContent = scopeText || 'Select a scope to start chatting';
}

async function loadChatConversation() {
    if (!currentChatScope) return;

    try {
        let url;
        if (currentChatScope === 'project') {
            url = apiUrl('/chat/project');
        } else {
            url = apiUrl(`/chat/${currentChatScope}/${currentChatScopeId}`);
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Failed to load conversation');
        }

        currentConversation = await response.json();

        // Set model if conversation has one
        if (currentConversation.model) {
            document.getElementById('chat-model-select').value = currentConversation.model;
        }

        renderChatMessages();
    } catch (e) {
        console.error('Error loading conversation:', e);
        renderChatEmpty();
    }
}

function renderChatMessages() {
    const container = document.getElementById('chat-messages');

    if (!currentConversation || currentConversation.messages.length === 0) {
        container.innerHTML = `
            <div class="chat-empty-state">
                <p>Start a conversation about your story.</p>
                <p class="text-muted">The AI has access to your characters, world context, and scene summaries.</p>
            </div>
        `;
        return;
    }

    let html = '';
    for (const msg of currentConversation.messages) {
        html += renderChatMessage(msg);
    }

    container.innerHTML = html;

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function renderChatMessage(msg) {
    const timeStr = new Date(msg.timestamp).toLocaleTimeString();
    const editsHtml = msg.edits_made && msg.edits_made.length > 0
        ? renderChatEdits(msg.edits_made)
        : '';

    return `
        <div class="chat-message ${msg.role}">
            <div class="chat-message-content">${escapeHtml(msg.content)}</div>
            ${editsHtml}
            <div class="chat-message-meta">
                <span>${timeStr}</span>
            </div>
        </div>
    `;
}

function renderChatEdits(edits) {
    if (!edits || edits.length === 0) return '';

    let html = '<div class="chat-message-edits">';
    for (const edit of edits) {
        html += `
            <div class="chat-edit-item">
                <span class="edit-type">${escapeHtml(edit.entity_type)}</span>
                <span>Updated <strong>${escapeHtml(edit.field)}</strong> on ${escapeHtml(edit.entity_id)}</span>
            </div>
        `;
    }
    html += '</div>';
    return html;
}

function renderChatEmpty() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
        <div class="chat-empty-state">
            <p>Select a scope above to start a conversation.</p>
            <p class="text-muted">The AI has access to your characters, world context, and scene summaries.</p>
        </div>
    `;
}

function showChatLoading() {
    const container = document.getElementById('chat-messages');
    const loadingHtml = `
        <div class="chat-loading" id="chat-loading-indicator">
            <div class="chat-loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <span>Thinking...</span>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', loadingHtml);
    container.scrollTop = container.scrollHeight;
}

function hideChatLoading() {
    const loading = document.getElementById('chat-loading-indicator');
    if (loading) loading.remove();
}

function updateChatSendButton() {
    const input = document.getElementById('chat-input');
    const btn = document.getElementById('chat-send-btn');
    btn.disabled = !input.value.trim() || chatSending || !currentChatScope;
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message || chatSending || !currentChatScope) return;

    chatSending = true;
    updateChatSendButton();

    // Add user message to UI immediately
    const userMsg = {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
        edits_made: []
    };

    if (!currentConversation) {
        currentConversation = { messages: [] };
    }
    currentConversation.messages.push(userMsg);
    renderChatMessages();

    // Clear input
    input.value = '';

    // Show loading
    showChatLoading();

    try {
        let url;
        if (currentChatScope === 'project') {
            url = apiUrl('/chat/project/message');
        } else {
            url = apiUrl(`/chat/${currentChatScope}/${currentChatScopeId}/message`);
        }

        const model = document.getElementById('chat-model-select').value || undefined;

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, model })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send message');
        }

        const data = await response.json();

        // Add assistant response
        currentConversation.messages.push(data.message);

        // Show edit indicator if edits were made
        if (data.edits_applied && data.edits_applied.length > 0) {
            showEditIndicator(data.edits_applied.length);
            // Refresh data since edits were made
            await loadAllData();
        }

        hideChatLoading();
        renderChatMessages();

    } catch (e) {
        hideChatLoading();
        // Remove the user message we added
        currentConversation.messages.pop();
        renderChatMessages();
        alert('Error sending message: ' + e.message);
    } finally {
        chatSending = false;
        updateChatSendButton();
    }
}

function showEditIndicator(count) {
    const indicator = document.getElementById('chat-edit-indicator');
    const countEl = document.getElementById('chat-edit-count');
    countEl.textContent = `${count} change${count > 1 ? 's' : ''} made`;
    indicator.style.display = 'flex';

    // Hide after 5 seconds
    setTimeout(() => {
        indicator.style.display = 'none';
    }, 5000);
}

async function clearChatConversation() {
    if (!currentChatScope) return;
    if (!confirm('Clear this conversation history?')) return;

    try {
        let url;
        if (currentChatScope === 'project') {
            url = apiUrl('/chat/project');
        } else {
            url = apiUrl(`/chat/${currentChatScope}/${currentChatScopeId}`);
        }

        await fetch(url, { method: 'DELETE' });

        currentConversation = null;
        renderChatEmpty();
        document.getElementById('chat-edit-indicator').style.display = 'none';
    } catch (e) {
        alert('Error clearing conversation: ' + e.message);
    }
}

// Setup chat input events
document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('input', updateChatSendButton);
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }
});

// ============================================
// Import Functions (Outline & Characters)
// ============================================
let importPreviewData = null;
let currentImportType = 'outline';

function showImportOutlineModal() {
    document.getElementById('import-outline-modal').style.display = 'block';
    document.getElementById('import-step-input').style.display = 'block';
    document.getElementById('import-step-preview').style.display = 'none';
    document.getElementById('import-step-progress').style.display = 'none';
    document.getElementById('import-step-complete').style.display = 'none';
    selectImportType('outline');
    document.getElementById('import-markdown').focus();
}

function hideImportOutlineModal() {
    document.getElementById('import-outline-modal').style.display = 'none';
    document.getElementById('import-markdown').value = '';
    document.getElementById('import-file').value = '';
    document.getElementById('import-file-name').textContent = '';
    importPreviewData = null;
    currentImportType = 'outline';
}

function selectImportType(type) {
    currentImportType = type;

    // Update active button
    document.querySelectorAll('.import-type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === type);
    });

    // Update help text and placeholder
    const helpText = document.getElementById('import-help-text');
    const textarea = document.getElementById('import-markdown');

    if (type === 'outline') {
        helpText.textContent = 'Paste your outline in Markdown format. Use # for Acts (optional), ## for Chapters, and ### for Scenes.';
        textarea.placeholder = `# Act I: The Beginning

## Chapter 1: First Steps

### Scene 1: Opening
The protagonist wakes to find their world changed...`;
    } else if (type === 'characters') {
        helpText.textContent = 'Paste characters in YAML format (instant parsing) or free-form text (AI parsing). YAML format recommended for large imports.';
        textarea.placeholder = `---
name: Elena Blackwood
role: Protagonist
age: 28
occupation: Archaeologist
personality_traits: Curious, Determined, Skeptical
background: Born in London to academics, she discovered her passion for archaeology at age 12.
---

---
name: Marcus Chen
role: Supporting
age: 32
occupation: Research Partner
personality_traits: Analytical, Loyal, Reserved
background: Elena's trusted partner with expertise in ancient languages.
---

(Or paste free-form text and AI will extract characters)`;
    }
}

function handleImportFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const validTypes = ['.txt', '.md', '.markdown'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validTypes.includes(ext)) {
        alert('Please upload a .txt or .md file');
        event.target.value = '';
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('import-markdown').value = e.target.result;
        document.getElementById('import-file-name').textContent = `Loaded: ${file.name}`;
    };
    reader.onerror = function() {
        alert('Error reading file');
    };
    reader.readAsText(file);
}

function previewImport() {
    if (currentImportType === 'outline') {
        previewOutlineImport();
    } else if (currentImportType === 'characters') {
        previewCharactersImport();
    }
}

function confirmImport() {
    if (currentImportType === 'outline') {
        confirmOutlineImport();
    } else if (currentImportType === 'characters') {
        confirmCharactersImport();
    }
}

async function previewOutlineImport() {
    const markdown = document.getElementById('import-markdown').value.trim();

    if (!markdown) {
        alert('Please enter some markdown outline text');
        return;
    }

    if (markdown.length < 20) {
        alert('Outline is too short. Please enter a more detailed outline.');
        return;
    }

    try {
        const response = await fetch(apiUrl('/outline/preview'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ markdown, preview_only: true })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to parse outline');
        }

        importPreviewData = await response.json();

        // Update preview UI
        document.getElementById('import-act-count').textContent = importPreviewData.acts.length;
        document.getElementById('import-chapter-count').textContent = importPreviewData.chapters.length;
        document.getElementById('import-scene-count').textContent = importPreviewData.scenes.length;

        // Render acts list
        const actsList = document.getElementById('import-acts-list');
        if (importPreviewData.acts.length === 0) {
            actsList.innerHTML = '<li class="text-muted">No acts (optional)</li>';
        } else {
            actsList.innerHTML = importPreviewData.acts.map(a =>
                `<li><strong>${escapeHtml(a.title)}</strong></li>`
            ).join('');
        }

        // Render chapters list
        const chaptersList = document.getElementById('import-chapters-list');
        if (importPreviewData.chapters.length === 0) {
            chaptersList.innerHTML = '<li class="text-muted">No chapters found</li>';
        } else {
            chaptersList.innerHTML = importPreviewData.chapters.map(ch =>
                `<li><strong>Ch ${ch.chapter_number}:</strong> ${escapeHtml(ch.title)}</li>`
            ).join('');
        }

        // Render scenes list
        const scenesList = document.getElementById('import-scenes-list');
        if (importPreviewData.scenes.length === 0) {
            scenesList.innerHTML = '<li class="text-muted">No scenes found</li>';
        } else {
            scenesList.innerHTML = importPreviewData.scenes.map(s =>
                `<li><strong>${escapeHtml(s.title)}</strong>${s.outline ? ' - ' + escapeHtml(s.outline.substring(0, 50)) + '...' : ''}</li>`
            ).join('');
        }

        // Show warnings if any
        const warningsEl = document.getElementById('import-warnings');
        if (importPreviewData.warnings.length > 0) {
            warningsEl.innerHTML = '<strong>Warnings:</strong><ul>' +
                importPreviewData.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('') +
                '</ul>';
            warningsEl.style.display = 'block';
        } else {
            warningsEl.style.display = 'none';
        }

        // Switch to preview step
        document.getElementById('import-step-input').style.display = 'none';
        document.getElementById('import-step-preview').style.display = 'block';
        document.getElementById('import-outline-preview').style.display = 'grid';
        document.getElementById('import-characters-preview').style.display = 'none';

    } catch (e) {
        alert('Error parsing outline: ' + e.message);
    }
}

function backToImportInput() {
    document.getElementById('import-step-preview').style.display = 'none';
    document.getElementById('import-step-input').style.display = 'block';
}

async function confirmOutlineImport() {
    const markdown = document.getElementById('import-markdown').value.trim();

    if (!markdown) {
        alert('No outline to import');
        return;
    }

    // Show progress
    document.getElementById('import-step-preview').style.display = 'none';
    document.getElementById('import-step-progress').style.display = 'block';

    try {
        const response = await fetch(apiUrl('/outline/import'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ markdown, preview_only: false })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to import outline');
        }

        const result = await response.json();

        // Show complete step
        document.getElementById('import-step-progress').style.display = 'none';
        document.getElementById('import-step-complete').style.display = 'block';
        document.getElementById('import-result-message').textContent =
            `Imported ${result.acts_created} act(s), ${result.chapters_created} chapter(s), and ${result.scenes_created} scene(s).`;

        // Refresh all data
        await loadAllData();

    } catch (e) {
        document.getElementById('import-step-progress').style.display = 'none';
        document.getElementById('import-step-preview').style.display = 'block';
        alert('Error importing outline: ' + e.message);
    }
}

// Character Import Functions - with auto-detect for structured YAML

// Try to parse structured YAML character blocks directly (no AI needed)
function tryParseStructuredCharacters(text) {
    const characters = [];

    // Split by --- lines, looking for YAML blocks with name: field
    const blocks = text.split(/\n---\s*\n/);

    for (const block of blocks) {
        const trimmed = block.trim();
        if (!trimmed) continue;

        // Check if this looks like a YAML block (has name: field)
        const nameMatch = trimmed.match(/^name:\s*(.+)$/m);
        if (!nameMatch) continue;

        // Parse YAML-like fields
        const char = { name: nameMatch[1].trim() };

        // Extract common fields
        const roleMatch = trimmed.match(/^role:\s*(.+)$/m);
        if (roleMatch) char.role = roleMatch[1].trim();

        const ageMatch = trimmed.match(/^age:\s*(\d+)/m);
        if (ageMatch) char.age = parseInt(ageMatch[1]);

        const occupationMatch = trimmed.match(/^occupation:\s*(.+)$/m);
        if (occupationMatch) char.occupation = occupationMatch[1].trim();

        const backgroundMatch = trimmed.match(/^background:\s*(.+)$/m);
        if (backgroundMatch) char.background = backgroundMatch[1].trim();

        // Parse personality_traits (can be comma-separated or YAML list)
        const traitsMatch = trimmed.match(/^personality_traits:\s*(.+)$/m);
        if (traitsMatch) {
            const traitsStr = traitsMatch[1].trim();
            // Handle comma-separated format
            char.personality_traits = traitsStr.split(',').map(t => t.trim()).filter(t => t);
        } else {
            // Try YAML list format
            const traitsListMatch = trimmed.match(/personality_traits:\s*\n((?:\s*-\s*.+\n?)+)/m);
            if (traitsListMatch) {
                char.personality_traits = traitsListMatch[1]
                    .split('\n')
                    .map(line => line.replace(/^\s*-\s*/, '').trim())
                    .filter(t => t);
            }
        }

        characters.push(char);
    }

    return characters;
}

async function previewCharactersImport() {
    const text = document.getElementById('import-markdown').value.trim();

    if (!text) {
        alert('Please enter character descriptions');
        return;
    }

    if (text.length < 20) {
        alert('Text is too short. Please enter more detailed character descriptions.');
        return;
    }

    const previewBtn = document.querySelector('#import-step-input button[onclick="previewImport()"]');
    const originalBtnText = previewBtn.textContent;

    try {
        let characters = [];
        let warnings = [];
        let parseMethod = '';

        // First, try structured YAML parsing (fast, no API call)
        const structuredChars = tryParseStructuredCharacters(text);

        if (structuredChars.length >= 1) {
            // Structured parsing worked
            characters = structuredChars;
            parseMethod = 'structured';
            console.log(`Parsed ${characters.length} characters using structured YAML format`);
        } else {
            // Fall back to AI parsing
            previewBtn.textContent = 'Parsing with AI...';
            previewBtn.disabled = true;

            const response = await fetch(apiUrl('/characters/import/parse'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, preview_only: true })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to parse characters');
            }

            const result = await response.json();
            characters = result.characters;
            warnings = result.warnings || [];
            parseMethod = 'ai';
        }

        importPreviewData = { characters, warnings };

        if (characters.length === 0) {
            alert('No characters could be extracted from the text. Try adding more detail or check the warnings.');
            if (warnings.length > 0) {
                console.log('Warnings:', warnings);
            }
            return;
        }

        // Show preview UI
        document.getElementById('import-step-input').style.display = 'none';
        document.getElementById('import-step-preview').style.display = 'block';
        document.getElementById('import-outline-preview').style.display = 'none';
        document.getElementById('import-characters-preview').style.display = 'block';

        // Update character count with parse method indicator
        const methodLabel = parseMethod === 'structured' ? ' (YAML)' : ' (AI)';
        document.getElementById('import-char-count').textContent = characters.length + methodLabel;

        // Render character list
        const listEl = document.getElementById('import-characters-list');
        listEl.innerHTML = characters.map((char, idx) => `
            <div class="import-character-item">
                <h5>${escapeHtml(char.name)}</h5>
                <div class="char-meta">
                    ${char.role ? `<span class="char-badge">${escapeHtml(char.role)}</span>` : ''}
                    ${char.age ? `<span>Age: ${char.age}</span>` : ''}
                    ${char.occupation ? `<span>${escapeHtml(char.occupation)}</span>` : ''}
                </div>
                ${char.personality_traits && char.personality_traits.length > 0 ?
                    `<div class="char-traits">${char.personality_traits.map(t => `<span class="trait-tag">${escapeHtml(t)}</span>`).join('')}</div>` : ''}
                ${char.background ? `<div class="char-preview">${escapeHtml(char.background.substring(0, 200))}${char.background.length > 200 ? '...' : ''}</div>` : ''}
                ${char.goals && char.goals.length > 0 ? `<div class="char-goals"><strong>Goals:</strong> ${char.goals.map(g => escapeHtml(g)).join(', ')}</div>` : ''}
            </div>
        `).join('');

        // Show warnings if any
        if (warnings.length > 0) {
            const warningsHtml = `<div class="import-warnings"><strong>Warnings:</strong> ${warnings.join('; ')}</div>`;
            listEl.insertAdjacentHTML('beforebegin', warningsHtml);
        }

    } catch (e) {
        alert('Error parsing characters: ' + e.message);
    } finally {
        previewBtn.textContent = originalBtnText;
        previewBtn.disabled = false;
    }
}

async function confirmCharactersImport() {
    if (!importPreviewData || !importPreviewData.characters || importPreviewData.characters.length === 0) {
        alert('No characters to import');
        return;
    }

    // Show progress
    document.getElementById('import-step-preview').style.display = 'none';
    document.getElementById('import-step-progress').style.display = 'block';

    try {
        // Call the confirm endpoint with all parsed characters
        const response = await fetch(apiUrl('/characters/import/confirm'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(importPreviewData.characters)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to import characters');
        }

        const result = await response.json();

        // Show complete step
        document.getElementById('import-step-progress').style.display = 'none';
        document.getElementById('import-step-complete').style.display = 'block';

        let message = `Imported ${result.imported} character(s).`;
        if (result.failed > 0) {
            message += ` ${result.failed} failed.`;
        }
        if (result.errors && result.errors.length > 0) {
            message += ` Errors: ${result.errors.join(', ')}`;
        }
        document.getElementById('import-result-message').textContent = message;

        // Refresh character list
        await loadCharacters();

        // Auto-close modal after brief delay and switch to Characters tab
        setTimeout(() => {
            hideImportOutlineModal();
            switchView('characters');
        }, 1500);

    } catch (e) {
        document.getElementById('import-step-progress').style.display = 'none';
        document.getElementById('import-step-preview').style.display = 'block';
        alert('Error importing characters: ' + e.message);
    }
}

// ============================================
// Queue Management
// ============================================
async function loadQueue(statusFilter = null) {
    try {
        let url = apiUrl('/generations/queue');
        if (statusFilter) {
            url += `?status=${statusFilter}`;
        }
        console.log('Loading queue from:', url);
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load queue');
        queueData = await response.json();
        console.log('Loaded queue data:', queueData.length, 'items');
        renderQueue();
        updateQueueBadge();
    } catch (e) {
        console.error('Error loading queue:', e);
    }
}

function renderQueue() {
    const list = document.getElementById('queue-list');
    if (!list) {
        console.error('queue-list element not found');
        return;
    }
    const filterEl = document.getElementById('queue-filter');
    const filter = filterEl ? filterEl.value : '';

    // Filter data if needed
    let filtered = queueData;
    if (filter) {
        filtered = queueData.filter(g => g.status === filter);
    }

    // Update stats
    const total = queueData.length;
    const inProgress = queueData.filter(g => ['generating', 'critiquing', 'revising', 'generating_summary'].includes(g.status)).length;
    const awaitingReview = queueData.filter(g => g.status === 'awaiting_approval').length;
    const completed = queueData.filter(g => g.status === 'completed').length;

    document.getElementById('queue-stat-total').textContent = total;
    document.getElementById('queue-stat-progress').textContent = inProgress;
    document.getElementById('queue-stat-review').textContent = awaitingReview;
    document.getElementById('queue-stat-done').textContent = completed;

    if (filtered.length === 0) {
        list.innerHTML = '<div class="empty-state">No generations match this filter</div>';
        return;
    }

    list.innerHTML = filtered.map(gen => {
        const scene = scenes.find(s => s.id === gen.scene_id);
        const sceneTitle = scene ? scene.title : gen.scene_id;
        const statusLabel = getStatusMessage(gen.status);

        return `
            <div class="queue-item" onclick="openQueueReview('${gen.generation_id}')">
                <div class="queue-item-info">
                    <div class="queue-item-title">${escapeHtml(sceneTitle)}</div>
                    <div class="queue-item-meta">
                        <span>Iteration ${gen.current_iteration}</span>
                        <span>${formatRelativeTime(gen.updated_at)}</span>
                    </div>
                </div>
                <div class="queue-item-status">
                    <span class="queue-status-badge ${gen.status}">${statusLabel}</span>
                </div>
            </div>
        `;
    }).join('');
}

function filterQueue() {
    renderQueue();
}

async function refreshQueue() {
    const filter = document.getElementById('queue-filter').value;
    await loadQueue(filter || null);
}

function startQueuePolling() {
    if (queuePollingInterval) return;
    queuePollingInterval = setInterval(async () => {
        await loadQueue();
        checkForNewReadyItems();
    }, 4000);
}

function stopQueuePolling() {
    if (queuePollingInterval) {
        clearInterval(queuePollingInterval);
        queuePollingInterval = null;
    }
}

function checkForNewReadyItems() {
    const currentReadyCount = queueData.filter(g => g.status === 'awaiting_approval').length;
    if (currentReadyCount > previousQueueCount && previousQueueCount >= 0) {
        const newCount = currentReadyCount - previousQueueCount;
        showToast('Ready for Review', `${newCount} generation(s) ready for review`, 'warning');
    }
    previousQueueCount = currentReadyCount;
}

function updateQueueBadge() {
    const badge = document.getElementById('queue-badge');
    const awaitingCount = queueData.filter(g => g.status === 'awaiting_approval').length;

    if (awaitingCount > 0) {
        badge.textContent = awaitingCount;
        badge.style.display = 'inline-flex';
    } else {
        badge.style.display = 'none';
    }
}

function openQueueReview(generationId) {
    console.log('openQueueReview called with:', generationId);
    console.log('queueData length:', queueData.length);

    const gen = queueData.find(g => g.generation_id === generationId);
    if (!gen) {
        console.log('Generation not found in queueData');
        // Try reloading queue
        loadQueue().then(() => {
            const retryGen = queueData.find(g => g.generation_id === generationId);
            if (retryGen) {
                showQueueReviewPanel(retryGen);
            } else {
                alert('Could not find generation. Please refresh the page.');
            }
        });
        return;
    }

    console.log('Found generation:', gen.status);

    // Find index in awaiting approval list
    const awaitingList = queueData.filter(g => g.status === 'awaiting_approval');
    currentQueueReviewIndex = awaitingList.findIndex(g => g.generation_id === generationId);
    if (currentQueueReviewIndex < 0) currentQueueReviewIndex = 0;

    showQueueReviewPanel(gen);
}

function showQueueReviewPanel(gen) {
    console.log('showQueueReviewPanel called for:', gen.generation_id);
    const panel = document.getElementById('queue-review-panel');
    if (!panel) {
        console.error('queue-review-panel not found!');
        return;
    }
    panel.style.display = 'block';
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    console.log('Panel should now be visible');

    const scene = scenes.find(s => s.id === gen.scene_id);
    const sceneTitle = scene ? scene.title : gen.scene_id;

    document.getElementById('queue-review-title').textContent = sceneTitle;
    document.getElementById('queue-review-iteration').textContent = gen.current_iteration;
    document.getElementById('queue-review-prose').textContent = gen.current_prose || '';
    document.getElementById('queue-review-critique').textContent = gen.current_critique || '';

    // Word count
    const prose = gen.current_prose || '';
    const wordCount = prose.trim() ? prose.trim().split(/\s+/).length : 0;
    document.getElementById('queue-review-word-count').textContent = `${wordCount.toLocaleString()} words`;

    // Position in queue
    const awaitingList = queueData.filter(g => g.status === 'awaiting_approval');
    const pos = currentQueueReviewIndex + 1;
    document.getElementById('queue-review-position').textContent = `${pos} of ${awaitingList.length}`;

    // Update nav buttons
    document.getElementById('queue-prev-btn').disabled = currentQueueReviewIndex === 0;
    document.getElementById('queue-next-btn').disabled = currentQueueReviewIndex >= awaitingList.length - 1;

    // Store current gen id for actions
    panel.dataset.genId = gen.generation_id;
}

function closeQueueReview() {
    document.getElementById('queue-review-panel').style.display = 'none';
}

function queuePrev() {
    const awaitingList = queueData.filter(g => g.status === 'awaiting_approval');
    if (currentQueueReviewIndex > 0) {
        currentQueueReviewIndex--;
        showQueueReviewPanel(awaitingList[currentQueueReviewIndex]);
    }
}

function queueNext() {
    const awaitingList = queueData.filter(g => g.status === 'awaiting_approval');
    if (currentQueueReviewIndex < awaitingList.length - 1) {
        currentQueueReviewIndex++;
        showQueueReviewPanel(awaitingList[currentQueueReviewIndex]);
    }
}

async function queueApproveAndRevise() {
    const panel = document.getElementById('queue-review-panel');
    const genId = panel.dataset.genId;
    if (!genId) return;

    try {
        const response = await fetch(apiUrl(`/generations/${genId}/approve`), {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to approve');
        }

        showToast('Revision Started', 'Revising based on critique...', 'info');
        closeQueueReview();
        await loadQueue();

    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function queueAcceptFinal() {
    const panel = document.getElementById('queue-review-panel');
    const genId = panel.dataset.genId;
    if (!genId) return;

    try {
        const response = await fetch(apiUrl(`/generations/${genId}/accept`), {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to accept');
        }

        showToast('Accepted', 'Scene saved as canon!', 'success');
        closeQueueReview();
        await loadQueue();
        await loadAllData(); // Refresh scenes to show canon status

        // Auto-advance to next if available
        const awaitingList = queueData.filter(g => g.status === 'awaiting_approval');
        if (awaitingList.length > 0) {
            currentQueueReviewIndex = Math.min(currentQueueReviewIndex, awaitingList.length - 1);
            showQueueReviewPanel(awaitingList[currentQueueReviewIndex]);
        }

    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function queueReject() {
    const panel = document.getElementById('queue-review-panel');
    const genId = panel.dataset.genId;
    if (!genId) return;

    if (!confirm('Reject this generation?')) return;

    try {
        await fetch(apiUrl(`/generations/${genId}/reject`), {
            method: 'POST'
        });

        closeQueueReview();
        await loadQueue();

    } catch (e) {
        console.error('Error rejecting:', e);
    }
}

// ============================================
// Batch Generation
// ============================================
function toggleSceneSelection(sceneId, event) {
    event.stopPropagation();
    console.log('toggleSceneSelection called:', sceneId);
    if (selectedScenes.has(sceneId)) {
        selectedScenes.delete(sceneId);
    } else {
        selectedScenes.add(sceneId);
    }
    console.log('selectedScenes:', Array.from(selectedScenes));
    updateBatchControls();
    renderOutlineTree();
}

function updateBatchControls() {
    const controls = document.getElementById('batch-controls');
    const count = document.getElementById('batch-count');

    if (selectedScenes.size > 0) {
        if (!controls) {
            // Create batch controls if they don't exist
            const sidebar = document.getElementById('sidebar');
            const footer = sidebar.querySelector('.sidebar-footer');
            const batchDiv = document.createElement('div');
            batchDiv.id = 'batch-controls';
            batchDiv.className = 'batch-controls';
            batchDiv.innerHTML = `
                <span class="batch-count" id="batch-count">${selectedScenes.size} selected</span>
                <button class="btn btn-success btn-small" onclick="startBatchGeneration()">Generate Selected</button>
                <button class="btn btn-secondary btn-small" onclick="clearSelection()">Clear</button>
            `;
            footer.insertBefore(batchDiv, footer.firstChild);
        } else {
            document.getElementById('batch-count').textContent = `${selectedScenes.size} selected`;
        }
    } else {
        if (controls) {
            controls.remove();
        }
    }
}

function clearSelection() {
    selectedScenes.clear();
    updateBatchControls();
    renderOutlineTree();
}

async function startBatchGeneration() {
    console.log('startBatchGeneration called');
    console.log('selectedScenes:', Array.from(selectedScenes));

    if (selectedScenes.size === 0) {
        alert('No scenes selected');
        return;
    }

    const genModel = document.getElementById('gen-model')?.value || undefined;
    const critiqueModel = document.getElementById('critique-model')?.value || undefined;
    console.log('Using models:', genModel, critiqueModel);

    const sceneIds = Array.from(selectedScenes);
    let started = 0;
    let failed = 0;

    for (const sceneId of sceneIds) {
        console.log('Starting generation for:', sceneId);
        try {
            const url = apiUrl('/generations/start');
            console.log('POST to:', url);
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    scene_id: sceneId,
                    max_iterations: 99,
                    generation_model: genModel,
                    critique_model: critiqueModel
                })
            });

            console.log('Response status:', response.status);
            if (response.ok) {
                started++;
            } else {
                const errorData = await response.json();
                console.error('Generation failed:', errorData);
                failed++;
            }
        } catch (e) {
            failed++;
            console.error('Error starting generation for', sceneId, e);
        }
    }

    showToast('Batch Started', `Started ${started} generation(s)${failed > 0 ? `, ${failed} failed` : ''}`, 'success');

    // Clear selection and switch to queue view
    clearSelection();
    startQueuePolling();
    navigateToView('queue');
    await loadQueue();
}

async function generateChapter(chapterId, event) {
    event.stopPropagation();

    const chapterScenes = scenes.filter(s => s.chapter_id === chapterId && !s.is_canon);
    if (chapterScenes.length === 0) {
        alert('No non-canon scenes in this chapter');
        return;
    }

    if (!confirm(`Generate ${chapterScenes.length} scene(s) in this chapter?`)) return;

    const genModel = document.getElementById('gen-model')?.value || undefined;
    const critiqueModel = document.getElementById('critique-model')?.value || undefined;

    let started = 0;
    for (const scene of chapterScenes) {
        try {
            const response = await fetch(apiUrl('/generations/start'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    scene_id: scene.id,
                    max_iterations: 99,
                    generation_model: genModel,
                    critique_model: critiqueModel
                })
            });

            if (response.ok) started++;
        } catch (e) {
            console.error('Error starting generation for', scene.id, e);
        }
    }

    showToast('Chapter Generation Started', `Started ${started} scene(s)`, 'success');
    startQueuePolling();
    navigateToView('queue');
    await loadQueue();
}

// ============================================
// Toast Notifications
// ============================================
function showToast(title, message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <div class="toast-title">${escapeHtml(title)}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
    `;

    toast.onclick = () => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    };

    container.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
}

function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

// ============================================
// Utility Functions
// ============================================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
