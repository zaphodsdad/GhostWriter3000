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
let currentRevisionMode = 'full';
let previousProse = null;  // For diff view
let showingDiff = false;   // Diff view toggle state
let diffChanges = [];      // Array of {id, type, value, accepted} for inline accept/reject
let diffOldText = null;    // Store old text for rebuilding prose
let currentSelection = null;  // For selection-based revision {text, start, end}
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

// Credit alert state
let creditAlertSettings = { threshold: 5, enabled: true };
let lastCreditAlertShown = 0; // Prevent spam

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

// Reading view editing state
let readingDirty = false;           // Has unsaved changes
let readingOriginalProse = null;    // Original prose before edits
let readingCurrentProse = null;     // Current edited prose
let pendingNavigation = null;       // Navigation to perform after save/discard

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

        // Populate default model dropdowns
        populateSettingsModelDropdowns(data.default_generation_model, data.default_critique_model);

        // Load credit alert settings
        const thresholdInput = document.getElementById('settings-credit-threshold');
        const alertsEnabledInput = document.getElementById('settings-credit-alerts-enabled');
        if (thresholdInput) thresholdInput.value = data.credit_alert_threshold || 5;
        if (alertsEnabledInput) alertsEnabledInput.checked = data.credit_alerts_enabled !== false;

        // Update global credit alert settings
        creditAlertSettings.threshold = data.credit_alert_threshold || 5;
        creditAlertSettings.enabled = data.credit_alerts_enabled !== false;

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

function populateSettingsModelDropdowns(currentGenModel, currentCritiqueModel) {
    const genSelect = document.getElementById('settings-default-gen-model');
    const critiqueSelect = document.getElementById('settings-default-critique-model');

    if (!genSelect || !critiqueSelect) return;

    // Use availableModels from the global list (loaded on page load)
    if (availableModels.length === 0) {
        genSelect.innerHTML = '<option value="">Models not loaded</option>';
        critiqueSelect.innerHTML = '<option value="">Models not loaded</option>';
        return;
    }

    // Helper to get model display name
    const getModelName = (modelId) => {
        if (!modelId) return 'Not Set';
        const model = availableModels.find(m => m.id === modelId);
        if (model) return model.name;
        const baseId = modelId.replace(/-\d{8}$/, '');
        const partialMatch = availableModels.find(m => m.id.startsWith(baseId) || m.id.includes(baseId.split('/')[1]));
        if (partialMatch) return partialMatch.name;
        return modelId.split('/').pop().replace(/-/g, ' ').replace(/\d{8}$/, '').trim();
    };

    // Group models by provider
    const modelsByProvider = {};
    availableModels.forEach(model => {
        const provider = model.id.split('/')[0];
        if (!modelsByProvider[provider]) {
            modelsByProvider[provider] = [];
        }
        modelsByProvider[provider].push(model);
    });

    const providerNames = {
        'anthropic': 'Anthropic',
        'openai': 'OpenAI',
        'google': 'Google',
        'meta-llama': 'Meta Llama',
        'mistralai': 'Mistral AI',
        'cohere': 'Cohere',
        'deepseek': 'DeepSeek',
        'qwen': 'Qwen'
    };

    // Build options with system default shown
    const genDefaultName = systemGenModel ? getModelName(systemGenModel) : 'Not Set';
    let genOptionsHtml = `<option value="">Default Model - ${genDefaultName}</option>`;

    const critiqueDefaultName = systemCritiqueModel ? getModelName(systemCritiqueModel) : 'Not Set';
    let critiqueOptionsHtml = `<option value="">Default Model - ${critiqueDefaultName}</option>`;

    for (const [provider, models] of Object.entries(modelsByProvider)) {
        const providerLabel = providerNames[provider] || provider;
        const optgroup = `<optgroup label="${providerLabel}">`;
        let modelOptions = '';
        models.forEach(model => {
            modelOptions += `<option value="${model.id}">${model.name}</option>`;
        });
        genOptionsHtml += optgroup + modelOptions + '</optgroup>';
        critiqueOptionsHtml += optgroup + modelOptions + '</optgroup>';
    }

    genSelect.innerHTML = genOptionsHtml;
    critiqueSelect.innerHTML = critiqueOptionsHtml;

    // Set current values
    if (currentGenModel) genSelect.value = currentGenModel;
    if (currentCritiqueModel) critiqueSelect.value = currentCritiqueModel;
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
    const defaultGenModel = document.getElementById('settings-default-gen-model').value;
    const defaultCritiqueModel = document.getElementById('settings-default-critique-model').value;
    const creditThreshold = parseFloat(document.getElementById('settings-credit-threshold').value) || 5;
    const creditAlertsEnabled = document.getElementById('settings-credit-alerts-enabled').checked;

    // Build update object - only include non-empty values for keys
    const update = {};
    if (openrouterKey) update.openrouter_api_key = openrouterKey;
    if (anthropicKey) update.anthropic_api_key = anthropicKey;
    if (customUrl) update.custom_endpoint_url = customUrl;
    if (customKey) update.custom_endpoint_key = customKey;

    // Always include model settings (empty string means use system default)
    update.default_generation_model = defaultGenModel || null;
    update.default_critique_model = defaultCritiqueModel || null;

    // Always include credit alert settings
    update.credit_alert_threshold = creditThreshold;
    update.credit_alerts_enabled = creditAlertsEnabled;

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
// Start Page Settings Panel
// ============================================
let startSettingsExpanded = false;

function toggleStartSettings() {
    const panel = document.getElementById('start-settings-panel');
    const body = document.getElementById('start-settings-body');
    startSettingsExpanded = !startSettingsExpanded;

    if (startSettingsExpanded) {
        body.style.display = 'block';
        panel.classList.add('expanded');
        loadStartSettings();
    } else {
        body.style.display = 'none';
        panel.classList.remove('expanded');
    }
}

async function loadStartSettings() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();

        // Store system defaults for display in dropdowns
        systemGenModel = data.system_generation_model || '';
        systemCritiqueModel = data.system_critique_model || '';

        // Update status indicators
        updateStartKeyStatus('openrouter', data.openrouter_api_key_set);
        updateStartKeyStatus('anthropic', data.anthropic_api_key_set);

        // Load data directory info
        if (data.data_dir) {
            document.getElementById('start-data-dir-current').textContent = data.data_dir;
        }
        if (data.data_dir_from) {
            const sourceEl = document.getElementById('start-data-dir-source');
            sourceEl.textContent = data.data_dir_from;
            sourceEl.className = 'badge' + (data.data_dir_from === 'config' ? ' canon' : '');
        }

        // Populate default model dropdowns (pass system defaults for display)
        populateStartModelDropdowns(data.default_generation_model, data.default_critique_model);

        // Load credit alert settings
        const thresholdInput = document.getElementById('start-credit-threshold');
        const alertsEnabledInput = document.getElementById('start-credit-alerts-enabled');
        if (thresholdInput) thresholdInput.value = data.credit_alert_threshold || 5;
        if (alertsEnabledInput) alertsEnabledInput.checked = data.credit_alerts_enabled !== false;

        // Clear the input fields (we don't send back actual keys for security)
        document.getElementById('start-openrouter-key').value = '';
        document.getElementById('start-anthropic-key').value = '';
        document.getElementById('start-data-dir').value = '';

        // Re-populate workspace dropdowns if they exist (uses stored system defaults)
        populateModelDropdowns();

    } catch (e) {
        console.error('Failed to load start settings:', e);
    }
}

function updateStartKeyStatus(provider, isSet) {
    const statusEl = document.getElementById(`start-${provider}-key-status`);
    if (!statusEl) return;

    if (isSet) {
        statusEl.textContent = 'Key is configured';
        statusEl.className = 'key-status set';
    } else {
        statusEl.textContent = 'No key set';
        statusEl.className = 'key-status not-set';
    }
}

function populateStartModelDropdowns(currentGenModel, currentCritiqueModel) {
    const genSelect = document.getElementById('start-default-gen-model');
    const critiqueSelect = document.getElementById('start-default-critique-model');

    if (!genSelect || !critiqueSelect) return;

    // Use availableModels from the global list (loaded on page load)
    if (availableModels.length === 0) {
        genSelect.innerHTML = '<option value="">Models not loaded</option>';
        critiqueSelect.innerHTML = '<option value="">Models not loaded</option>';
        return;
    }

    // Helper to get model display name
    const getModelName = (modelId) => {
        if (!modelId) return 'Not Set';
        const model = availableModels.find(m => m.id === modelId);
        if (model) return model.name;
        const baseId = modelId.replace(/-\d{8}$/, '');
        const partialMatch = availableModels.find(m => m.id.startsWith(baseId) || m.id.includes(baseId.split('/')[1]));
        if (partialMatch) return partialMatch.name;
        return modelId.split('/').pop().replace(/-/g, ' ').replace(/\d{8}$/, '').trim();
    };

    // Group models by provider
    const modelsByProvider = {};
    availableModels.forEach(model => {
        const provider = model.id.split('/')[0];
        if (!modelsByProvider[provider]) {
            modelsByProvider[provider] = [];
        }
        modelsByProvider[provider].push(model);
    });

    const providerNames = {
        'anthropic': 'Anthropic',
        'openai': 'OpenAI',
        'google': 'Google',
        'meta-llama': 'Meta Llama',
        'mistralai': 'Mistral AI',
        'cohere': 'Cohere',
        'deepseek': 'DeepSeek',
        'qwen': 'Qwen'
    };

    // Build options with system default shown
    const genDefaultName = systemGenModel ? getModelName(systemGenModel) : 'Not Set';
    let genOptionsHtml = `<option value="">Default Model - ${genDefaultName}</option>`;

    const critiqueDefaultName = systemCritiqueModel ? getModelName(systemCritiqueModel) : 'Not Set';
    let critiqueOptionsHtml = `<option value="">Default Model - ${critiqueDefaultName}</option>`;

    for (const [provider, models] of Object.entries(modelsByProvider)) {
        const providerLabel = providerNames[provider] || provider;
        const optgroup = `<optgroup label="${providerLabel}">`;
        let modelOptions = '';
        models.forEach(model => {
            modelOptions += `<option value="${model.id}">${model.name}</option>`;
        });
        const closeOptgroup = '</optgroup>';

        genOptionsHtml += optgroup + modelOptions + closeOptgroup;
        critiqueOptionsHtml += optgroup + modelOptions + closeOptgroup;
    }

    genSelect.innerHTML = genOptionsHtml;
    critiqueSelect.innerHTML = critiqueOptionsHtml;

    // Set current values
    if (currentGenModel) genSelect.value = currentGenModel;
    if (currentCritiqueModel) critiqueSelect.value = currentCritiqueModel;
}

async function saveStartSettings() {
    const openrouterKey = document.getElementById('start-openrouter-key').value.trim();
    const anthropicKey = document.getElementById('start-anthropic-key').value.trim();
    const defaultGenModel = document.getElementById('start-default-gen-model').value;
    const defaultCritiqueModel = document.getElementById('start-default-critique-model').value;
    const creditThreshold = parseFloat(document.getElementById('start-credit-threshold').value) || 5;
    const creditAlertsEnabled = document.getElementById('start-credit-alerts-enabled').checked;

    // Build update object - only include non-empty values for keys
    const update = {};
    if (openrouterKey) update.openrouter_api_key = openrouterKey;
    if (anthropicKey) update.anthropic_api_key = anthropicKey;

    // Always include model settings (empty string means use system default)
    update.default_generation_model = defaultGenModel || null;
    update.default_critique_model = defaultCritiqueModel || null;

    // Always include credit alert settings
    update.credit_alert_threshold = creditThreshold;
    update.credit_alerts_enabled = creditAlertsEnabled;

    try {
        const response = await fetch('/api/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update)
        });

        if (response.ok) {
            showToast('Success', 'Settings saved successfully', 'success');
            // Reload settings to show updated status
            loadStartSettings();
            // Reload credits display
            loadStartCredits();
            // Reload models if API key was added
            if (openrouterKey) {
                loadAvailableModels();
            }
        } else {
            const error = await response.json();
            showToast('Error', `Failed to save: ${error.detail || 'Unknown error'}`, 'error');
        }
    } catch (e) {
        console.error('Failed to save settings:', e);
        showToast('Error', 'Failed to save settings', 'error');
    }
}

async function saveStartDataDir() {
    const newPath = document.getElementById('start-data-dir').value.trim();

    if (!newPath) {
        showToast('Error', 'Please enter a path', 'error');
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
            showToast('Success', 'Data directory saved. Restart server to apply.', 'success');

            // Update the display
            document.getElementById('start-data-dir-current').textContent = data.data_dir;
            document.getElementById('start-data-dir-source').textContent = 'config (pending restart)';
            document.getElementById('start-data-dir').value = '';
        } else {
            showToast('Error', data.detail || 'Failed to save data directory', 'error');
        }
    } catch (e) {
        console.error('Failed to save data directory:', e);
        showToast('Error', 'Failed to save data directory', 'error');
    }
}

async function loadStartCredits() {
    const container = document.getElementById('start-credits-container');
    const valueEl = document.getElementById('start-credits-remaining');

    if (!container || !valueEl) return;

    try {
        const response = await fetch('/api/settings/credits');
        if (response.ok) {
            const data = await response.json();
            const remaining = data.remaining.toFixed(2);
            valueEl.textContent = `$${remaining}`;

            // Color based on threshold
            if (data.remaining < creditAlertSettings.threshold) {
                valueEl.style.color = 'var(--danger)';
            } else {
                valueEl.style.color = 'var(--success)';
            }
        } else {
            valueEl.textContent = '--';
        }
    } catch (e) {
        valueEl.textContent = '--';
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
    loadAvailableModels();
    loadCredits();
    loadStartCredits();
    setupSelectionTracking();
    setupReadingSelectionTracking();
    setInterval(checkHealth, 30000);
    setInterval(loadCredits, 300000); // Refresh credits every 5 minutes

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

    // Check for recovery data from previous session
    checkForRecovery();
});

// Scroll to top function
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// ============================================
// Model Selection
// ============================================
let availableModels = [];

async function loadAvailableModels() {
    try {
        const response = await fetch('/api/settings/models');
        if (!response.ok) throw new Error('Failed to fetch models');
        availableModels = await response.json();
        populateModelDropdowns();
    } catch (e) {
        console.warn('Could not load models:', e);
        // Use fallback models
        availableModels = [
            { id: 'anthropic/claude-sonnet-4', name: 'Claude Sonnet 4' },
            { id: 'anthropic/claude-opus-4', name: 'Claude Opus 4' },
            { id: 'anthropic/claude-sonnet-4.5', name: 'Claude Sonnet 4.5' },
            { id: 'anthropic/claude-opus-4.5', name: 'Claude Opus 4.5' },
            { id: 'openai/gpt-4o', name: 'GPT-4o' },
        ];
        populateModelDropdowns();
    }
}

// Store system defaults for display
let systemGenModel = '';
let systemCritiqueModel = '';

function populateModelDropdowns() {
    const genModelSelect = document.getElementById('gen-model');
    const critiqueModelSelect = document.getElementById('critique-model');

    if (!genModelSelect || !critiqueModelSelect) return;

    // Group models by provider
    const modelsByProvider = {};
    availableModels.forEach(model => {
        const provider = model.id.split('/')[0];
        if (!modelsByProvider[provider]) {
            modelsByProvider[provider] = [];
        }
        modelsByProvider[provider].push(model);
    });

    const providerNames = {
        'anthropic': 'Anthropic',
        'openai': 'OpenAI',
        'google': 'Google',
        'meta-llama': 'Meta Llama',
        'mistralai': 'Mistral AI',
        'cohere': 'Cohere',
        'deepseek': 'DeepSeek',
        'qwen': 'Qwen'
    };

    // Helper to get model display name from ID
    const getModelName = (modelId) => {
        if (!modelId) return 'Not Set';
        // Try to find in available models
        const model = availableModels.find(m => m.id === modelId);
        if (model) return model.name;
        // Try partial match (in case version suffix differs)
        const baseId = modelId.replace(/-\d{8}$/, ''); // Remove date suffix like -20250514
        const partialMatch = availableModels.find(m => m.id.startsWith(baseId) || m.id.includes(baseId.split('/')[1]));
        if (partialMatch) return partialMatch.name;
        // Fallback to cleaned-up ID
        return modelId.split('/').pop().replace(/-/g, ' ').replace(/\d{8}$/, '').trim();
    };

    // Build HTML with optgroups - for generation
    const genDefaultName = systemGenModel ? getModelName(systemGenModel) : 'Not Set';
    let genOptionsHtml = `<option value="">Default Model - ${genDefaultName}</option>`;

    for (const [provider, models] of Object.entries(modelsByProvider)) {
        const providerLabel = providerNames[provider] || provider;
        genOptionsHtml += `<optgroup label="${providerLabel}">`;
        models.forEach(model => {
            const priceInfo = model.pricing_prompt
                ? ` ($${model.pricing_prompt.toFixed(2)}/M)`
                : '';
            genOptionsHtml += `<option value="${model.id}">${model.name}${priceInfo}</option>`;
        });
        genOptionsHtml += '</optgroup>';
    }

    // Build HTML for critique
    const critiqueDefaultName = systemCritiqueModel ? getModelName(systemCritiqueModel) : 'Not Set';
    let critiqueOptionsHtml = `<option value="">Default Model - ${critiqueDefaultName}</option>`;

    for (const [provider, models] of Object.entries(modelsByProvider)) {
        const providerLabel = providerNames[provider] || provider;
        critiqueOptionsHtml += `<optgroup label="${providerLabel}">`;
        models.forEach(model => {
            const priceInfo = model.pricing_prompt
                ? ` ($${model.pricing_prompt.toFixed(2)}/M)`
                : '';
            critiqueOptionsHtml += `<option value="${model.id}">${model.name}${priceInfo}</option>`;
        });
        critiqueOptionsHtml += '</optgroup>';
    }

    genModelSelect.innerHTML = genOptionsHtml;
    critiqueModelSelect.innerHTML = critiqueOptionsHtml;
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
// Edit Project
// ============================================
function showEditProjectModal() {
    if (!currentProject) return;

    document.getElementById('edit-project-title').value = currentProject.title || '';
    document.getElementById('edit-project-description').value = currentProject.description || '';
    document.getElementById('edit-project-author').value = currentProject.author || '';
    document.getElementById('edit-project-genre').value = currentProject.genre || '';

    document.getElementById('edit-project-modal').style.display = 'flex';
    document.getElementById('edit-project-title').focus();
}

function hideEditProjectModal() {
    document.getElementById('edit-project-modal').style.display = 'none';
}

async function saveProjectEdits() {
    if (!currentProject) return;

    const title = document.getElementById('edit-project-title').value.trim();
    const description = document.getElementById('edit-project-description').value.trim();
    const author = document.getElementById('edit-project-author').value.trim();
    const genre = document.getElementById('edit-project-genre').value.trim();

    if (!title) {
        alert('Title is required');
        return;
    }

    try {
        const response = await fetch(`/api/projects/${currentProject.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                description: description || null,
                author: author || null,
                genre: genre || null
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update project');
        }

        const updated = await response.json();

        // Update local state
        currentProject.title = updated.title;
        currentProject.description = updated.description;
        currentProject.author = updated.author;
        currentProject.genre = updated.genre;

        // Update UI
        document.getElementById('current-project-title').textContent = updated.title;
        document.getElementById('current-project-description').textContent =
            updated.description || 'No description';

        hideEditProjectModal();
        showToast('Success', 'Project updated', 'success');

        // Refresh project list in case title changed
        loadProjects();

    } catch (e) {
        alert('Error updating project: ' + e.message);
    }
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

// ============================================
// WORD COUNT GOAL MODAL
// ============================================

function showWordCountGoalModal() {
    const modal = document.getElementById('word-count-goal-modal');
    const input = document.getElementById('word-count-goal-input');

    // Pre-fill with current goal
    input.value = currentProject?.word_count_goal || '';

    modal.style.display = 'flex';
    input.focus();
}

function hideWordCountGoalModal() {
    document.getElementById('word-count-goal-modal').style.display = 'none';
}

function setWordCountGoal(value) {
    document.getElementById('word-count-goal-input').value = value;
}

async function saveWordCountGoal() {
    const input = document.getElementById('word-count-goal-input');
    const goal = input.value ? parseInt(input.value) : null;

    try {
        const response = await fetch(apiUrl(''), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word_count_goal: goal })
        });

        if (!response.ok) throw new Error('Failed to save word count goal');

        // Update local project data
        currentProject.word_count_goal = goal;

        // Recalculate and update display
        const canonScenes = scenes.filter(s => s.is_canon);
        let wordCount = 0;
        canonScenes.forEach(s => {
            if (s.prose) wordCount += s.prose.split(/\s+/).length;
        });
        updateWordCountDisplay(wordCount);

        hideWordCountGoalModal();
        showToast('Success', goal ? `Word count goal set to ${goal.toLocaleString()}` : 'Word count goal cleared', 'success');

    } catch (e) {
        alert('Error saving word count goal: ' + e.message);
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
    const revisionMode = document.querySelector('input[name="revision-mode"]:checked')?.value || 'full';

    try {
        const response = await fetch(apiUrl('/generations/start-edit'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scene_id: sceneId,
                max_iterations: 5,
                generation_model: genModel || undefined,
                critique_model: critiqueModel || undefined,
                revision_mode: revisionMode
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start edit mode');
        }

        const state = await response.json();
        currentGenId = state.generation_id;
        currentGenModel = genModel || 'Default';
        currentCritiqueModel = critiqueModel || 'Default';
        currentRevisionMode = revisionMode;

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
                    <div class="outline-scene ${s.is_canon ? 'canon' : ''}" onclick="openSceneWorkspace('${s.id}')">
                        ${!s.is_canon ? `<input type="checkbox" class="batch-checkbox" ${selectedScenes.has(s.id) ? 'checked' : ''} onclick="toggleSceneSelection('${s.id}', event)">` : ''}
                        ${escapeHtml(s.title)}
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ============================================
// Outline View (Full Outline Tab with Beats)
// ============================================

function renderOutlineView() {
    const container = document.getElementById('outline-view-tree');
    if (!container) return;

    if (chapters.length === 0) {
        container.innerHTML = `
            <div class="outline-empty">
                <h3>No Structure Yet</h3>
                <p>Create chapters and scenes in the Structure tab first, then plan your beats here.</p>
            </div>
        `;
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
        const actChapterList = (actChapters[act.id] || []).sort((a, b) =>
            (a.chapter_number || 0) - (b.chapter_number || 0)
        );

        html += `
            <div class="outline-act">
                <div class="outline-act-header" onclick="toggleOutlineSection(this)">
                    <span class="outline-act-title">${escapeHtml(act.title)}</span>
                    <span>${actChapterList.length} chapters</span>
                </div>
                <div class="outline-act-content">
                    ${actChapterList.map(ch => renderOutlineViewChapter(ch)).join('')}
                </div>
            </div>
        `;
    });

    // Render chapters without acts
    if (noActChapters.length > 0) {
        noActChapters.sort((a, b) => (a.chapter_number || 0) - (b.chapter_number || 0));
        html += `
            <div class="outline-act">
                <div class="outline-act-header" onclick="toggleOutlineSection(this)">
                    <span class="outline-act-title">Unassigned Chapters</span>
                    <span>${noActChapters.length} chapters</span>
                </div>
                <div class="outline-act-content">
                    ${noActChapters.map(ch => renderOutlineViewChapter(ch)).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

function renderOutlineViewChapter(chapter) {
    const chapterScenes = scenes.filter(s => s.chapter_id === chapter.id);
    chapterScenes.sort((a, b) => (a.scene_number || 0) - (b.scene_number || 0));

    return `
        <div class="outline-chapter">
            <div class="outline-chapter-header" onclick="toggleOutlineSection(this)">
                <span class="outline-chapter-title">Chapter ${chapter.chapter_number || '?'}: ${escapeHtml(chapter.title)}</span>
                <span>${chapterScenes.length} scenes</span>
            </div>
            <div class="outline-chapter-content">
                ${chapterScenes.map(s => renderOutlineViewScene(s)).join('')}
                ${chapterScenes.length === 0 ? '<p class="text-muted" style="padding: 10px;">No scenes in this chapter</p>' : ''}
            </div>
        </div>
    `;
}

function renderOutlineViewScene(scene) {
    const beats = scene.beats || [];
    const status = scene.outline_status || 'idea';

    return `
        <div class="outline-scene" data-scene-id="${scene.id}">
            <div class="outline-scene-header" onclick="toggleOutlineSection(this)">
                <span class="outline-scene-title">${escapeHtml(scene.title)}</span>
                <div class="outline-scene-status">
                    <span class="outline-status-badge ${status}">${status}</span>
                    <span>${beats.length} beats</span>
                </div>
            </div>
            <div class="outline-scene-content">
                <div class="outline-scene-outline">${escapeHtml(scene.outline || 'No outline')}</div>

                <div class="beats-section">
                    <div class="beats-header">
                        <span class="beats-title">Beats</span>
                    </div>
                    <div class="beats-list" id="beats-${scene.id}">
                        ${beats.length > 0 ? beats.map((beat, idx) => renderBeat(scene.id, beat, idx)).join('') : ''}
                    </div>
                    <button class="add-beat-btn" onclick="openBeatEditor('${scene.id}', null, event)">
                        + Add Beat
                    </button>
                </div>
            </div>
        </div>
    `;
}

function renderBeat(sceneId, beat, index) {
    const tags = beat.tags || [];
    return `
        <div class="beat-item" data-beat-id="${beat.id}">
            <span class="beat-number">${index + 1}</span>
            <div class="beat-content">
                <div class="beat-text">${escapeHtml(beat.text)}</div>
                ${beat.notes ? `<div class="beat-notes">${escapeHtml(beat.notes)}</div>` : ''}
                ${tags.length > 0 ? `
                    <div class="beat-tags">
                        ${tags.map(t => `<span class="beat-tag">#${escapeHtml(t)}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
            <div class="beat-actions">
                <button class="beat-action-btn" onclick="openBeatEditor('${sceneId}', '${beat.id}', event)" title="Edit">Edit</button>
                <button class="beat-action-btn delete" onclick="deleteBeat('${sceneId}', '${beat.id}', event)" title="Delete">Del</button>
            </div>
        </div>
    `;
}

function toggleOutlineSection(header) {
    const content = header.nextElementSibling;
    if (content) {
        content.style.display = content.style.display === 'none' ? 'block' : 'none';
    }
}

// Beat Editor Modal
function openBeatEditor(sceneId, beatId, event) {
    if (event) event.stopPropagation();

    document.getElementById('beat-scene-id').value = sceneId;
    document.getElementById('beat-id').value = beatId || '';

    // Clear form
    document.getElementById('beat-text').value = '';
    document.getElementById('beat-notes').value = '';
    document.getElementById('beat-tags').value = '';

    if (beatId) {
        // Editing existing beat - find and populate
        const scene = scenes.find(s => s.id === sceneId);
        if (scene && scene.beats) {
            const beat = scene.beats.find(b => b.id === beatId);
            if (beat) {
                document.getElementById('beat-text').value = beat.text || '';
                document.getElementById('beat-notes').value = beat.notes || '';
                document.getElementById('beat-tags').value = (beat.tags || []).join(', ');
            }
        }
        document.getElementById('beat-editor-title').textContent = 'Edit Beat';
    } else {
        document.getElementById('beat-editor-title').textContent = 'Add Beat';
    }

    document.getElementById('beat-editor-modal').style.display = 'flex';
}

function closeBeatEditor() {
    document.getElementById('beat-editor-modal').style.display = 'none';
}

async function saveBeat(event) {
    event.preventDefault();

    const sceneId = document.getElementById('beat-scene-id').value;
    const beatId = document.getElementById('beat-id').value;
    const text = document.getElementById('beat-text').value.trim();
    const notes = document.getElementById('beat-notes').value.trim();
    const tagsRaw = document.getElementById('beat-tags').value;
    const tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim().replace(/^#/, '')).filter(t => t) : [];

    if (!text) {
        showToast('Beat text is required', 'error');
        return;
    }

    try {
        let url, method, body;

        if (beatId) {
            // Update existing beat
            url = apiUrl(`/scenes/${sceneId}/beats/${beatId}`);
            method = 'PUT';
            body = { text, notes: notes || null, tags };
        } else {
            // Create new beat
            url = apiUrl(`/scenes/${sceneId}/beats`);
            method = 'POST';
            body = { text, notes: notes || null, tags };
        }

        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to save beat');
        }

        closeBeatEditor();

        // Refresh scenes to get updated beats
        await loadScenes();
        renderOutlineView();

        showToast(beatId ? 'Beat updated' : 'Beat added', 'success');

    } catch (err) {
        console.error('Error saving beat:', err);
        showToast(err.message, 'error');
    }
}

async function deleteBeat(sceneId, beatId, event) {
    if (event) event.stopPropagation();

    if (!confirm('Delete this beat?')) return;

    try {
        const response = await fetch(
            apiUrl(`/scenes/${sceneId}/beats/${beatId}`),
            { method: 'DELETE' }
        );

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to delete beat');
        }

        // Refresh scenes to get updated beats
        await loadScenes();
        renderOutlineView();

        showToast('Beat deleted', 'success');

    } catch (err) {
        console.error('Error deleting beat:', err);
        showToast(err.message, 'error');
    }
}

// ============================================
// Story Structure Templates
// ============================================

async function openTemplateModal() {
    document.getElementById('template-modal').style.display = 'flex';
    document.getElementById('template-clear-existing').checked = false;
    await loadTemplates();
}

function closeTemplateModal() {
    document.getElementById('template-modal').style.display = 'none';
}

async function loadTemplates() {
    const container = document.getElementById('template-list');
    container.innerHTML = '<p class="text-muted">Loading templates...</p>';

    try {
        const response = await fetch('/api/projects/templates/list');
        if (!response.ok) throw new Error('Failed to load templates');

        const templates = await response.json();

        container.innerHTML = `
            <div class="template-grid">
                ${templates.map(t => `
                    <div class="template-card" data-template-id="${t.id}">
                        <h4>${escapeHtml(t.name)}</h4>
                        <p>${escapeHtml(t.description)}</p>
                        <div class="template-stats">
                            <span>${t.act_count} acts</span>
                            <span>${t.scene_count} scenes</span>
                        </div>
                        <button class="btn btn-primary apply-btn" onclick="applyTemplate('${t.id}', event)">
                            Apply This Template
                        </button>
                    </div>
                `).join('')}
            </div>
        `;

    } catch (err) {
        console.error('Error loading templates:', err);
        container.innerHTML = '<p class="text-muted">Failed to load templates. Please try again.</p>';
    }
}

async function applyTemplate(templateId, event) {
    if (event) event.stopPropagation();

    const clearExisting = document.getElementById('template-clear-existing').checked;

    if (clearExisting) {
        if (!confirm('This will DELETE all existing acts, chapters, and scenes. Are you sure?')) {
            return;
        }
    }

    const btn = event.target;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Applying...';

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/apply-template`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                template_id: templateId,
                clear_existing: clearExisting
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to apply template');
        }

        const result = await response.json();

        // Refresh data
        await loadActs();
        await loadChapters();
        await loadScenes();
        renderOutlineView();
        renderStructureTree();
        renderOutlineTree();

        closeTemplateModal();
        showToast(`Applied ${result.template_name}: ${result.created.acts} acts, ${result.created.chapters} chapters, ${result.created.scenes} scenes`, 'success');

    } catch (err) {
        console.error('Error applying template:', err);
        showToast(err.message, 'error');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// ============================================
// Clear All Structure (Nuclear Delete)
// ============================================

async function confirmClearAllStructure() {
    // First confirmation
    if (!confirm('This will DELETE all acts, chapters, scenes, and beats from this project.\n\nThis action cannot be undone.\n\nAre you sure?')) {
        return;
    }

    // Second confirmation for extra safety
    if (!confirm('FINAL WARNING: All outline structure will be permanently deleted.\n\nA backup will be created, but are you absolutely sure?')) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/structure`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to clear structure');
        }

        const result = await response.json();

        // Refresh all data
        await loadActs();
        await loadChapters();
        await loadScenes();
        renderOutlineView();
        renderStructureTree();
        renderOutlineTree();

        showToast(`Cleared: ${result.deleted.acts} acts, ${result.deleted.chapters} chapters, ${result.deleted.scenes} scenes`, 'success');

    } catch (err) {
        console.error('Error clearing structure:', err);
        showToast(err.message, 'error');
    }
}

// ============================================
// Auto-Generate Outline
// ============================================

let generatedOutline = null;  // Store generated outline for review/apply

const SCOPE_ESTIMATES = {
    quick: { scenes: 9, beats: 27, cost: "$0.08" },
    standard: { scenes: 15, beats: 60, cost: "$0.18" },
    detailed: { scenes: 24, beats: 120, cost: "$0.35" }
};

// Store clear existing preference when generation starts
let autoGenClearExisting = false;

function openAutoGenerateModal() {
    document.getElementById('auto-generate-modal').style.display = 'flex';
    document.getElementById('auto-gen-seed').value = '';
    document.getElementById('auto-gen-genre').value = '';
    document.getElementById('auto-gen-scope').value = 'standard';
    document.getElementById('auto-gen-budget').value = '';
    document.getElementById('auto-gen-clear-existing').checked = false;
    updateAutoGenEstimate();
}

function closeAutoGenerateModal() {
    document.getElementById('auto-generate-modal').style.display = 'none';
}

function updateAutoGenEstimate() {
    const scope = document.getElementById('auto-gen-scope').value;
    const estimate = SCOPE_ESTIMATES[scope] || SCOPE_ESTIMATES.standard;

    document.getElementById('auto-gen-estimate-items').textContent =
        `~${estimate.scenes} scenes, ~${estimate.beats} beats`;
    document.getElementById('auto-gen-estimate-cost').textContent =
        `~${estimate.cost}`;
}

async function startAutoGenerate(mode) {
    const seed = document.getElementById('auto-gen-seed').value.trim();
    if (!seed) {
        showToast('Please enter a story premise', 'error');
        return;
    }

    const genre = document.getElementById('auto-gen-genre').value || null;
    const scope = document.getElementById('auto-gen-scope').value;
    const budgetStr = document.getElementById('auto-gen-budget').value;
    const budget = budgetStr ? parseFloat(budgetStr) : null;

    // Store clear existing preference before closing modal
    autoGenClearExisting = document.getElementById('auto-gen-clear-existing').checked;

    closeAutoGenerateModal();

    if (mode === 'full') {
        await runFullGeneration(seed, scope, genre, budget);
    } else {
        await runStagedGeneration(seed, scope, genre, budget);
    }
}

async function runFullGeneration(seed, scope, genre, budget) {
    // Show progress modal
    const progressModal = document.getElementById('auto-generate-progress-modal');
    const progressStatus = document.getElementById('auto-gen-progress-status');

    progressModal.style.display = 'flex';
    progressStatus.textContent = 'Working on it...';

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/auto-generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                seed,
                scope,
                mode: 'full',
                genre,
                budget_limit: budget
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Generation failed');
        }

        const result = await response.json();

        progressStatus.textContent = 'Generation complete!';

        // Brief pause to show completion
        await new Promise(r => setTimeout(r, 500));

        progressModal.style.display = 'none';

        if (result.success) {
            if (result.partial) {
                showToast(`Generation stopped at ${result.stopped_at} (budget limit reached)`, 'warning');
            }
            const costMsg = result.usage ? ` (Cost: ${result.usage.cost_formatted})` : '';
            showToast(`Outline generated!${costMsg}`, 'success');
            generatedOutline = result.outline;
            showOutlineReview(result.outline, result.usage);
        } else {
            throw new Error(result.error || 'Generation failed');
        }

    } catch (err) {
        progressModal.style.display = 'none';
        console.error('Auto-generation error:', err);
        showToast(err.message, 'error');
    }
}

async function runStagedGeneration(seed, scope, genre, budget) {
    // For staged mode, we start with acts only
    const progressModal = document.getElementById('auto-generate-progress-modal');
    const progressStatus = document.getElementById('auto-gen-progress-status');

    progressModal.style.display = 'flex';
    progressStatus.textContent = 'Generating act structure...';

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/auto-generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                seed,
                scope,
                mode: 'staged',
                level: 'acts',
                genre
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Generation failed');
        }

        const result = await response.json();

        await new Promise(r => setTimeout(r, 300));
        progressModal.style.display = 'none';

        if (result.success) {
            // For staged mode, show acts for review first
            // TODO: Implement staged review UI where user can approve acts,
            // then generate chapters, etc.
            showToast('Staged generation: Acts generated. Full staged UI coming soon!', 'info');
            console.log('Generated acts:', result.acts);

            // For now, wrap in outline structure and show review
            generatedOutline = {
                seed,
                scope,
                genre,
                acts: result.acts.map(a => ({ ...a, chapters: [] }))
            };
            showOutlineReview(generatedOutline, result.usage);
        } else {
            throw new Error(result.error || 'Generation failed');
        }

    } catch (err) {
        progressModal.style.display = 'none';
        console.error('Staged generation error:', err);
        showToast(err.message, 'error');
    }
}

function showOutlineReview(outline, usage) {
    const reviewModal = document.getElementById('auto-generate-review-modal');
    const reviewContent = document.getElementById('auto-gen-review-content');
    const reviewStats = document.getElementById('auto-gen-review-stats');

    // Count items
    let actCount = 0, chapterCount = 0, sceneCount = 0, beatCount = 0;

    let html = '<div class="generated-outline-tree">';

    for (const act of outline.acts || []) {
        actCount++;
        html += `
            <div class="gen-act">
                <div class="gen-act-header">
                    <strong>Act ${actCount}: ${escapeHtml(act.title)}</strong>
                </div>
                <div class="gen-act-desc text-muted">${escapeHtml(act.description || '')}</div>
        `;

        if (act.chapters && act.chapters.length > 0) {
            html += '<div class="gen-chapters">';
            for (const chapter of act.chapters) {
                chapterCount++;
                html += `
                    <div class="gen-chapter">
                        <div class="gen-chapter-header">
                            Chapter ${chapterCount}: ${escapeHtml(chapter.title)}
                        </div>
                        <div class="gen-chapter-desc text-muted">${escapeHtml(chapter.description || '')}</div>
                `;

                if (chapter.scenes && chapter.scenes.length > 0) {
                    html += '<div class="gen-scenes">';
                    for (const scene of chapter.scenes) {
                        sceneCount++;
                        html += `
                            <div class="gen-scene">
                                <div class="gen-scene-header">${escapeHtml(scene.title)}</div>
                                <div class="gen-scene-outline">${escapeHtml(scene.outline || '')}</div>
                        `;

                        if (scene.beats && scene.beats.length > 0) {
                            html += '<div class="gen-beats">';
                            for (const beat of scene.beats) {
                                beatCount++;
                                html += `<div class="gen-beat">• ${escapeHtml(beat.text)}</div>`;
                            }
                            html += '</div>';
                        }

                        html += '</div>';
                    }
                    html += '</div>';
                }

                html += '</div>';
            }
            html += '</div>';
        } else {
            html += '<div class="text-muted" style="padding: 8px 16px; font-style: italic;">No chapters generated yet (staged mode)</div>';
        }

        html += '</div>';
    }

    html += '</div>';

    reviewContent.innerHTML = html;

    // Update stats
    let statsText = `${actCount} acts`;
    if (chapterCount > 0) statsText += `, ${chapterCount} chapters`;
    if (sceneCount > 0) statsText += `, ${sceneCount} scenes`;
    if (beatCount > 0) statsText += `, ${beatCount} beats`;
    if (usage) statsText += ` • Cost: ${usage.cost_formatted}`;
    reviewStats.textContent = statsText;

    reviewModal.style.display = 'flex';
}

function closeAutoGenerateReviewModal() {
    document.getElementById('auto-generate-review-modal').style.display = 'none';
    generatedOutline = null;
}

async function applyGeneratedOutline() {
    if (!generatedOutline) {
        showToast('No outline to apply', 'error');
        return;
    }

    // Use the stored value from when generation was started
    const clearExisting = autoGenClearExisting;

    if (clearExisting) {
        if (!confirm('This will DELETE all existing acts, chapters, and scenes. Are you sure?')) {
            return;
        }
    }

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/auto-generate/apply?clear_existing=${clearExisting}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(generatedOutline)
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to apply outline');
        }

        const result = await response.json();

        closeAutoGenerateReviewModal();

        // Refresh data
        await loadActs();
        await loadChapters();
        await loadScenes();
        renderOutlineView();
        renderStructureTree();
        renderOutlineTree();

        showToast(`Applied outline: ${result.created.acts} acts, ${result.created.chapters} chapters, ${result.created.scenes} scenes, ${result.created.beats} beats`, 'success');

    } catch (err) {
        console.error('Error applying outline:', err);
        showToast(err.message, 'error');
    }
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

    // Handle backups view
    if (view === 'backups') {
        await loadBackups();
    }

    // Handle generate view - refresh scene dropdown
    if (view === 'generate') {
        populateFormSelects();
    }

    // Handle outline view
    if (view === 'outline') {
        renderOutlineView();
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
        loadReferences(),
        loadQueue()
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
    document.getElementById('stat-characters').textContent = characters.length;
    document.getElementById('stat-worlds').textContent = worlds.length;
    document.getElementById('stat-chapters').textContent = chapters.length;
    document.getElementById('stat-scenes').textContent = scenes.length;

    const canonScenes = scenes.filter(s => s.is_canon);
    document.getElementById('stat-canon').textContent = canonScenes.length;

    // Calculate word count from canon scenes
    let wordCount = 0;
    canonScenes.forEach(s => {
        if (s.prose) {
            wordCount += s.prose.split(/\s+/).length;
        }
    });
    document.getElementById('stat-words').textContent = wordCount.toLocaleString();

    // Update master word count in header with goal progress
    updateWordCountDisplay(wordCount);
}

function updateWordCountDisplay(wordCount) {
    document.getElementById('master-word-count').textContent = wordCount.toLocaleString();

    const goal = currentProject?.word_count_goal;
    const separatorEl = document.getElementById('word-count-separator');
    const goalEl = document.getElementById('word-count-goal');
    const progressEl = document.getElementById('word-count-progress');
    const progressFillEl = document.getElementById('word-count-progress-fill');

    if (goal && goal > 0) {
        separatorEl.style.display = 'inline';
        goalEl.style.display = 'inline';
        goalEl.textContent = goal.toLocaleString();
        progressEl.style.display = 'block';

        const percentage = Math.min((wordCount / goal) * 100, 100);
        progressFillEl.style.width = percentage + '%';

        if (wordCount >= goal) {
            progressFillEl.classList.add('complete');
        } else {
            progressFillEl.classList.remove('complete');
        }
    } else {
        separatorEl.style.display = 'none';
        goalEl.style.display = 'none';
        progressEl.style.display = 'none';
    }
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

    // Scene select for generation - sorted by chapter order, then scene number
    const genSelect = document.getElementById('gen-scene-select');
    if (genSelect) {
        const sortedScenes = scenes.filter(s => !s.is_canon).sort((a, b) => {
            const chA = chapters.find(ch => ch.id === a.chapter_id);
            const chB = chapters.find(ch => ch.id === b.chapter_id);
            const chNumA = chA ? chA.chapter_number : 999;
            const chNumB = chB ? chB.chapter_number : 999;
            if (chNumA !== chNumB) return chNumA - chNumB;
            return (a.scene_number || 0) - (b.scene_number || 0);
        });
        genSelect.innerHTML = '<option value="">-- Choose a Scene --</option>' +
            sortedScenes.map(s => {
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
                        <div class="structure-scene ${s.is_canon ? 'canon' : ''} ${isEditMode ? 'edit-mode' : ''}" onclick="openSceneWorkspace('${s.id}')">
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
    document.getElementById('scene-modal').style.display = 'flex';
    document.getElementById('scene-form-title').textContent = 'New Scene';
    document.getElementById('scene-chapter').focus();
}

function showSceneFormForChapter(chapterId) {
    showSceneForm();
    document.getElementById('scene-chapter').value = chapterId;
    document.getElementById('scene-title').focus();
}

function hideSceneForm() {
    document.getElementById('scene-modal').style.display = 'none';
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
    // Check for unsaved AI revision changes before switching
    if (readingDirty && currentReadingData && currentReadingData.id !== id) {
        showUnsavedChangesModal(() => {
            // Reset dirty state and recursively call after save/discard
            showReadingView(type, id);
        });
        return;
    }

    // Clear dirty state when loading new content
    if (currentReadingData && currentReadingData.id !== id) {
        setReadingDirty(false);
        readingOriginalProse = null;
        readingCurrentProse = null;
    }

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
            // Show edit mode status in subtitle
            if (data.edit_mode) {
                subtitle = data.is_canon ? 'Canon Scene (Edit Mode)' : 'Edit Mode - Ready for Critique';
            } else {
                subtitle = data.is_canon ? 'Canon Scene' : 'Not yet canon';
            }
            // Use original_prose if in edit mode and prose is empty
            prose = data.prose || data.original_prose || '';
            wordCount = data.word_count || 0;

            currentReadingData = { type, id, title, prose, is_canon: data.is_canon, edit_mode: data.edit_mode };
            document.getElementById('reference-btn').style.display = 'inline-flex';
            document.getElementById('edit-prose-btn').style.display = 'inline-flex';
            // Show canon toggle button if scene has prose
            const markCanonBtn = document.getElementById('mark-canon-btn');
            if (markCanonBtn) {
                if (prose && prose.trim()) {
                    markCanonBtn.style.display = 'inline-flex';
                    if (data.is_canon) {
                        markCanonBtn.textContent = 'Remove from Canon';
                        markCanonBtn.className = 'btn btn-warning';
                    } else {
                        markCanonBtn.textContent = 'Mark as Canon';
                        markCanonBtn.className = 'btn btn-success';
                    }
                } else {
                    markCanonBtn.style.display = 'none';
                }
            }

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
            document.getElementById('mark-canon-btn').style.display = 'none';

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
            document.getElementById('mark-canon-btn').style.display = 'none';

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
            document.getElementById('mark-canon-btn').style.display = 'none';
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

    // Check for unsaved AI revision changes
    if (readingDirty) {
        showUnsavedChangesModal(() => {
            const viewToShow = previousView || 'dashboard';
            navigateToView(viewToShow);
            currentReadingData = null;
        });
        return;
    }

    const viewToShow = previousView || 'dashboard';
    navigateToView(viewToShow);
    currentReadingData = null;
}

// Warn before closing browser tab with unsaved changes
window.addEventListener('beforeunload', (e) => {
    if (hasUnsavedChanges || readingDirty) {
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

async function toggleCanonFromReading() {
    if (!currentReadingData || currentReadingData.type !== 'scene') return;
    if (!currentReadingData.prose || !currentReadingData.prose.trim()) {
        alert('Cannot change canon status: scene has no prose content.');
        return;
    }

    const newCanonStatus = !currentReadingData.is_canon;
    const confirmMsg = newCanonStatus
        ? 'Mark this scene as canon? Canon scenes are included in the manuscript and used for continuity.'
        : 'Remove this scene from canon? It will no longer be included in the manuscript.';

    if (!confirm(confirmMsg)) {
        return;
    }

    try {
        const response = await fetch(apiUrl(`/scenes/${currentReadingData.id}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                is_canon: newCanonStatus
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update canon status');
        }

        // Update current data
        currentReadingData.is_canon = newCanonStatus;

        // Update button text and style
        const markCanonBtn = document.getElementById('mark-canon-btn');
        if (newCanonStatus) {
            markCanonBtn.textContent = 'Remove from Canon';
            markCanonBtn.className = 'btn btn-warning';
        } else {
            markCanonBtn.textContent = 'Mark as Canon';
            markCanonBtn.className = 'btn btn-success';
        }

        // Update subtitle
        if (newCanonStatus) {
            document.getElementById('reading-subtitle').textContent = currentReadingData.edit_mode ? 'Canon Scene (Edit Mode)' : 'Canon Scene';
        } else {
            document.getElementById('reading-subtitle').textContent = currentReadingData.edit_mode ? 'Edit Mode - Ready for Critique' : 'Not yet canon';
        }

        // Refresh data to update stats
        await loadScenes();
        await loadChapters();
        updateStats();
        renderOutlineTree();
        renderStructureTree();

    } catch (e) {
        alert('Error updating canon status: ' + e.message);
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
// Unified Scene Workspace
// ============================================
let currentWorkspaceScene = null;
let workspaceGenId = null;
let workspacePollingInterval = null;
let workspacePreviousProse = null;

async function openSceneWorkspace(sceneId) {
    // Fetch scene data
    try {
        const response = await fetch(apiUrl(`/scenes/${sceneId}`));
        if (!response.ok) throw new Error('Failed to load scene');
        const scene = await response.json();

        currentWorkspaceScene = scene;

        // Update header
        const chapter = chapters.find(c => c.id === scene.chapter_id);
        document.getElementById('ws-title').textContent = scene.title;
        document.getElementById('ws-subtitle').textContent = chapter ? `Chapter ${chapter.chapter_number}` : '';

        // Update badges
        document.getElementById('ws-status-badge').style.display = scene.prose ? 'inline-flex' : 'none';
        document.getElementById('ws-canon-badge').style.display = scene.is_canon ? 'inline-flex' : 'none';
        document.getElementById('ws-edit-mode-badge').style.display = scene.edit_mode ? 'inline-flex' : 'none';

        // Check for active generation in queue
        const activeStatuses = ['pending', 'generating', 'critiquing', 'awaiting_approval', 'revising'];
        const activeGen = queueData.find(g => g.scene_id === sceneId && activeStatuses.includes(g.status));

        // Determine state and show appropriate UI
        hideAllWorkspaceStates();

        if (scene.is_canon) {
            showWorkspaceCanon(scene);
        } else if (activeGen && activeGen.status === 'awaiting_approval') {
            // Has an active generation awaiting review - load it
            await loadGenerationForReview(activeGen.generation_id);
        } else if (activeGen && ['generating', 'critiquing', 'revising'].includes(activeGen.status)) {
            // Generation in progress - show generating state
            currentGenId = activeGen.generation_id;
            workspaceGenId = activeGen.generation_id;  // Also set for accept/reject buttons
            showWorkspaceGenerating();
            startGenerationPolling();
        } else if (scene.prose || scene.original_prose) {
            showWorkspaceProse(scene);
        } else {
            showWorkspaceEmpty(scene);
        }

        // Navigate to workspace
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.main-content .view').forEach(v => v.classList.remove('active'));
        document.getElementById('scene-workspace').classList.add('active');

        // Populate model dropdowns
        populateWorkspaceModelDropdowns();

    } catch (e) {
        console.error('Error opening workspace:', e);
        showToast('Error', 'Failed to load scene: ' + e.message, 'error');
    }
}

async function loadGenerationForReview(generationId) {
    try {
        const response = await fetch(apiUrl(`/generations/${generationId}`));
        if (!response.ok) throw new Error('Failed to load generation');
        const data = await response.json();

        currentGenId = generationId;
        workspaceGenId = generationId;  // Also set workspace gen ID for accept/reject buttons
        showWorkspaceReview(data);
    } catch (e) {
        console.error('Error loading generation for review:', e);
        showToast('Error', 'Failed to load generation: ' + e.message, 'error');
        // Fall back to empty state
        showWorkspaceEmpty(currentWorkspaceScene);
    }
}

function hideAllWorkspaceStates() {
    const states = ['ws-empty', 'ws-generating', 'ws-review', 'ws-prose', 'ws-canon', 'ws-editing', 'ws-import', 'ws-complete', 'ws-no-scene', 'ws-error'];
    states.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    // Hide all header actions
    document.getElementById('ws-header-actions').style.display = 'none';
    document.getElementById('ws-canon-actions').style.display = 'none';
    document.getElementById('ws-review-actions').style.display = 'none';
}

function showWorkspaceEmpty(scene) {
    document.getElementById('ws-outline-display').textContent = scene.outline || 'No outline yet.';
    document.getElementById('ws-empty').style.display = 'block';
}

function showWorkspaceProse(scene) {
    const prose = scene.prose || scene.original_prose || '';
    document.getElementById('ws-prose-content').textContent = prose;
    const wordCount = prose.trim() ? prose.trim().split(/\s+/).length : 0;
    document.getElementById('ws-prose-stats').textContent = `${wordCount.toLocaleString()} words`;
    document.getElementById('ws-dirty-indicator').style.display = 'none';
    document.getElementById('ws-prose').style.display = 'block';
    // Show header actions for prose state
    document.getElementById('ws-header-actions').style.display = 'flex';
}

function showWorkspaceCanon(scene) {
    document.getElementById('ws-canon-content').textContent = scene.prose || '';
    const wordCount = scene.prose ? scene.prose.trim().split(/\s+/).length : 0;
    document.getElementById('ws-canon-stats').textContent = `${wordCount.toLocaleString()} words`;
    document.getElementById('ws-canon').style.display = 'block';
    // Show canon actions in header
    document.getElementById('ws-canon-actions').style.display = 'flex';
}

function showWorkspaceGenerating() {
    document.getElementById('ws-generating').style.display = 'block';
    document.getElementById('ws-progress-fill').style.width = '10%';
    document.getElementById('ws-progress-status').textContent = 'Generation in progress...';
}

let workspacePollingActive = false;

async function startGenerationPolling() {
    if (workspacePollingActive || !currentGenId) return;
    workspacePollingActive = true;

    const pollInterval = 2000;
    const maxWait = 300000; // 5 minutes max
    const startTime = Date.now();

    const statusMessages = {
        'pending': 'Waiting to start...',
        'generating': 'Generating prose...',
        'critiquing': 'Getting AI critique...',
        'revising': 'Revising prose...',
        'awaiting_approval': 'Ready for review'
    };

    while (workspacePollingActive && Date.now() - startTime < maxWait) {
        try {
            const response = await fetch(apiUrl(`/generations/${currentGenId}`));
            if (!response.ok) {
                workspacePollingActive = false;
                break;
            }

            const data = await response.json();

            // Update progress status
            const statusEl = document.getElementById('ws-progress-status');
            if (statusEl) {
                statusEl.textContent = statusMessages[data.status] || data.status;
            }

            // Update progress bar based on status
            const progressEl = document.getElementById('ws-progress-fill');
            if (progressEl) {
                const progressMap = {
                    'pending': '10%',
                    'generating': '30%',
                    'critiquing': '60%',
                    'revising': '80%',
                    'awaiting_approval': '100%'
                };
                progressEl.style.width = progressMap[data.status] || '50%';
            }

            // Stop polling when generation reaches a terminal or review state
            if (['awaiting_approval', 'completed', 'error', 'rejected'].includes(data.status)) {
                workspacePollingActive = false;

                if (data.status === 'awaiting_approval') {
                    hideAllWorkspaceStates();
                    showWorkspaceReview(data);
                } else if (data.status === 'completed') {
                    hideAllWorkspaceStates();
                    await showWorkspaceComplete(data);
                } else if (data.status === 'error') {
                    hideAllWorkspaceStates();
                    showWorkspaceError(data.error_message || 'Generation failed');
                }
                return;
            }

            await new Promise(resolve => setTimeout(resolve, pollInterval));
        } catch (e) {
            console.error('Error polling generation:', e);
            workspacePollingActive = false;
            break;
        }
    }

    workspacePollingActive = false;
}

function stopGenerationPolling() {
    workspacePollingActive = false;
}

function populateWorkspaceModelDropdowns() {
    const genSelect = document.getElementById('ws-gen-model');
    const critiqueSelect = document.getElementById('ws-critique-model');

    if (!genSelect || !critiqueSelect || availableModels.length === 0) return;

    // Helper to get model display name
    const getModelName = (modelId) => {
        if (!modelId) return 'Not Set';
        const model = availableModels.find(m => m.id === modelId);
        if (model) return model.name;
        const baseId = modelId.replace(/-\d{8}$/, '');
        const partialMatch = availableModels.find(m => m.id.startsWith(baseId) || m.id.includes(baseId.split('/')[1]));
        if (partialMatch) return partialMatch.name;
        return modelId.split('/').pop().replace(/-/g, ' ').replace(/\d{8}$/, '').trim();
    };

    // Group models by provider
    const modelsByProvider = {};
    availableModels.forEach(model => {
        const provider = model.id.split('/')[0];
        if (!modelsByProvider[provider]) {
            modelsByProvider[provider] = [];
        }
        modelsByProvider[provider].push(model);
    });

    const providerNames = {
        'anthropic': 'Anthropic',
        'openai': 'OpenAI',
        'google': 'Google',
        'meta-llama': 'Meta Llama',
        'mistralai': 'Mistral AI',
        'cohere': 'Cohere',
        'deepseek': 'DeepSeek',
        'qwen': 'Qwen'
    };

    // Build options with default model name shown
    const genDefaultName = systemGenModel ? getModelName(systemGenModel) : 'Not Set';
    let genOptionsHtml = `<option value="">Default Model - ${genDefaultName}</option>`;

    const critiqueDefaultName = systemCritiqueModel ? getModelName(systemCritiqueModel) : 'Not Set';
    let critiqueOptionsHtml = `<option value="">Default Model - ${critiqueDefaultName}</option>`;

    for (const [provider, models] of Object.entries(modelsByProvider)) {
        const providerLabel = providerNames[provider] || provider;
        const optgroup = `<optgroup label="${providerLabel}">`;
        let modelOptions = '';
        models.forEach(model => {
            modelOptions += `<option value="${model.id}">${model.name}</option>`;
        });
        genOptionsHtml += optgroup + modelOptions + '</optgroup>';
        critiqueOptionsHtml += optgroup + modelOptions + '</optgroup>';
    }

    genSelect.innerHTML = genOptionsHtml;
    critiqueSelect.innerHTML = critiqueOptionsHtml;
}

function toggleWorkspaceSettings() {
    const body = document.getElementById('ws-settings-body');
    const toggle = document.getElementById('ws-settings-toggle');
    const isHidden = body.style.display === 'none';
    body.style.display = isHidden ? 'block' : 'none';
    toggle.textContent = isHidden ? '▼' : '▶';
}

function toggleCritiquePanel() {
    const columns = document.getElementById('ws-review-columns');
    if (!columns) return;

    const isCollapsed = columns.classList.contains('critique-collapsed');
    if (isCollapsed) {
        // Expand
        columns.classList.remove('critique-collapsed');
    } else {
        // Collapse
        columns.classList.add('critique-collapsed');
    }
}

async function startWorkspaceGeneration() {
    if (!currentWorkspaceScene) return;

    const genModel = document.getElementById('ws-gen-model').value || undefined;
    const critiqueModel = document.getElementById('ws-critique-model').value || undefined;
    const revisionMode = document.querySelector('input[name="ws-revision-mode"]:checked')?.value || 'full';

    // Validate models
    if (genModel && critiqueModel && genModel === critiqueModel) {
        showToast('Error', 'Generation and Critique models must be different', 'error');
        return;
    }

    try {
        // Cleanup old completed/rejected/error generations for this scene
        await fetch(apiUrl(`/generations/by-scene/${currentWorkspaceScene.id}?keep_active=true`), {
            method: 'DELETE'
        });

        hideAllWorkspaceStates();
        document.getElementById('ws-generating').style.display = 'block';
        updateWorkspaceProgress('initialized', 'Starting generation...');

        const response = await fetch(apiUrl('/generations/start'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scene_id: currentWorkspaceScene.id,
                max_iterations: 99,
                generation_model: genModel,
                critique_model: critiqueModel,
                revision_mode: revisionMode
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start generation');
        }

        const data = await response.json();
        workspaceGenId = data.generation_id;
        workspacePreviousProse = null;

        // Start polling
        startWorkspacePolling();

    } catch (e) {
        showToast('Error', 'Generation failed: ' + e.message, 'error');
        showWorkspaceEmpty(currentWorkspaceScene);
    }
}

function startWorkspacePolling() {
    workspacePollingInterval = setInterval(checkWorkspaceProgress, 2000);
}

function stopWorkspacePolling() {
    if (workspacePollingInterval) {
        clearInterval(workspacePollingInterval);
        workspacePollingInterval = null;
    }
}

async function checkWorkspaceProgress() {
    if (!workspaceGenId) return;

    try {
        const response = await fetch(apiUrl(`/generations/${workspaceGenId}`));
        const data = await response.json();

        updateWorkspaceProgress(data.status, getWorkspaceStatusMessage(data.status));

        if (data.status === 'awaiting_approval') {
            stopWorkspacePolling();
            showWorkspaceReview(data);
        } else if (data.status === 'completed') {
            stopWorkspacePolling();
            showWorkspaceComplete(data);
        } else if (data.status === 'error') {
            stopWorkspacePolling();
            showWorkspaceError(data.error_message || 'Generation failed');
        } else if (data.status === 'rejected') {
            stopWorkspacePolling();
            await refreshWorkspaceScene();
        }
    } catch (e) {
        console.error('Error checking progress:', e);
    }
}

function updateWorkspaceProgress(status, message) {
    const statusEl = document.getElementById('ws-progress-status');
    const detailEl = document.getElementById('ws-progress-detail');
    const fillEl = document.getElementById('ws-progress-fill');

    if (statusEl) statusEl.textContent = message;
    if (detailEl) detailEl.textContent = getWorkspaceStatusDetail(status);

    const progressMap = {
        'initialized': 10, 'generating': 30, 'generation_complete': 50,
        'critiquing': 70, 'awaiting_approval': 90, 'revising': 50,
        'generating_summary': 95, 'completed': 100
    };
    if (fillEl) fillEl.style.width = (progressMap[status] || 10) + '%';
}

function getWorkspaceStatusMessage(status) {
    const messages = {
        'initialized': 'Initializing...', 'generating': 'Generating prose...',
        'generation_complete': 'Generation complete', 'critiquing': 'Running AI critique...',
        'awaiting_approval': 'Ready for review', 'revising': 'Revising based on critique...',
        'generating_summary': 'Generating summary...', 'completed': 'Complete!'
    };
    return messages[status] || status;
}

function getWorkspaceStatusDetail(status) {
    const details = {
        'initialized': 'Setting up generation pipeline...',
        'generating': 'AI is writing your scene based on the outline...',
        'critiquing': 'AI is analyzing the prose for improvements...',
        'revising': 'AI is revising based on the critique...',
        'generating_summary': 'Creating continuity summary...'
    };
    return details[status] || '';
}

function showWorkspaceReview(data) {
    hideAllWorkspaceStates();

    // Reset critique panel to expanded state
    const columns = document.getElementById('ws-review-columns');
    if (columns) {
        columns.classList.remove('critique-collapsed');
    }

    // Reset dirty indicator
    document.getElementById('ws-review-dirty-indicator').style.display = 'none';

    document.getElementById('ws-iteration').textContent = data.current_iteration || data.iteration || 1;
    document.getElementById('ws-revision-mode-badge').textContent = data.revision_mode === 'polish' ? 'Polish' : 'Full';
    document.getElementById('ws-review-prose').textContent = data.current_prose || '';
    document.getElementById('ws-critique').textContent = data.current_critique || data.critique || '';

    const wordCount = data.current_prose ? data.current_prose.trim().split(/\s+/).length : 0;
    document.getElementById('ws-review-word-count').textContent = `${wordCount.toLocaleString()} words`;

    // Show diff button if we have previous prose
    const diffBtn = document.getElementById('ws-diff-toggle-btn');
    if (diffBtn) {
        diffBtn.style.display = workspacePreviousProse ? 'inline-flex' : 'none';
    }

    document.getElementById('ws-review').style.display = 'block';
    // Show review actions in header
    document.getElementById('ws-review-actions').style.display = 'flex';
    workspacePreviousProse = data.current_prose;
}

async function showWorkspaceComplete(data) {
    hideAllWorkspaceStates();

    document.getElementById('ws-summary').textContent = data.summary || 'Summary generated.';
    document.getElementById('ws-complete').style.display = 'block';

    // Refresh scene data and sidebar (await to ensure data is loaded before updating stats)
    await loadScenes();
    await loadChapters();
    updateStats();
    renderOutlineTree();
    renderStructureTree();

    // Refresh workspace scene data
    refreshWorkspaceScene();
}

function showWorkspaceError(errorMessage) {
    hideAllWorkspaceStates();
    document.getElementById('ws-error-message').textContent = errorMessage || 'An error occurred during generation.';
    document.getElementById('ws-error').style.display = 'block';
}

async function retryWorkspaceGeneration() {
    // Dismiss the error first (rejects the failed generation)
    if (workspaceGenId) {
        try {
            await fetch(apiUrl(`/generations/${workspaceGenId}/reject`), {
                method: 'POST'
            });
        } catch (e) {
            console.error('Failed to reject errored generation:', e);
        }
    }

    // Start a new generation
    workspaceGenId = null;
    await startWorkspaceGeneration();
}

async function dismissWorkspaceError() {
    // Reject the failed generation to clean up
    if (workspaceGenId) {
        try {
            await fetch(apiUrl(`/generations/${workspaceGenId}/reject`), {
                method: 'POST'
            });
        } catch (e) {
            console.error('Failed to reject errored generation:', e);
        }
    }

    workspaceGenId = null;
    await refreshWorkspaceScene();
}

async function workspaceApproveAndRevise() {
    if (!workspaceGenId) return;

    const instructions = document.getElementById('ws-revision-instructions')?.value || '';

    try {
        document.getElementById('ws-revise-btn-header').disabled = true;

        hideAllWorkspaceStates();
        document.getElementById('ws-generating').style.display = 'block';
        updateWorkspaceProgress('revising', 'Revising based on critique...');

        const response = await fetch(apiUrl(`/generations/${workspaceGenId}/approve`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_instructions: instructions || null })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to approve');
        }

        // Clear instructions
        const instructionsEl = document.getElementById('ws-revision-instructions');
        if (instructionsEl) instructionsEl.value = '';

        startWorkspacePolling();

    } catch (e) {
        showToast('Error', e.message, 'error');
        showWorkspaceReview({ current_prose: workspacePreviousProse });
    } finally {
        document.getElementById('ws-revise-btn-header').disabled = false;
    }
}

async function workspaceAcceptFinal() {
    if (!workspaceGenId) return;

    try {
        const response = await fetch(apiUrl(`/generations/${workspaceGenId}/accept`), {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to accept');
        }

        hideAllWorkspaceStates();
        document.getElementById('ws-generating').style.display = 'block';
        updateWorkspaceProgress('generating_summary', 'Generating summary...');

        startWorkspacePolling();

    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function workspaceReject() {
    if (!workspaceGenId) return;

    try {
        await fetch(apiUrl(`/generations/${workspaceGenId}/reject`), { method: 'POST' });
        workspaceGenId = null;
        workspacePreviousProse = null;
        await refreshWorkspaceScene();
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function refreshWorkspaceScene() {
    if (!currentWorkspaceScene) return;
    await openSceneWorkspace(currentWorkspaceScene.id);
}

function showWorkspaceImport() {
    hideAllWorkspaceStates();
    document.getElementById('ws-import-prose').value = '';
    document.getElementById('ws-import-word-count').textContent = '0 words';
    document.getElementById('ws-import').style.display = 'block';

    // Add word count tracking
    document.getElementById('ws-import-prose').oninput = function() {
        const words = this.value.trim() ? this.value.trim().split(/\s+/).length : 0;
        document.getElementById('ws-import-word-count').textContent = `${words.toLocaleString()} words`;
    };
}

async function confirmWorkspaceImport() {
    if (!currentWorkspaceScene) return;

    const prose = document.getElementById('ws-import-prose').value.trim();
    if (!prose) {
        showToast('Error', 'Please enter some prose to import', 'error');
        return;
    }

    try {
        // Enable edit mode and save prose
        const response = await fetch(apiUrl(`/scenes/${currentWorkspaceScene.id}/edit-mode`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ original_prose: prose })
        });

        if (!response.ok) throw new Error('Failed to import prose');

        showToast('Success', 'Prose imported. Ready for critique.', 'success');
        await refreshWorkspaceScene();

    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

function cancelWorkspaceImport() {
    refreshWorkspaceScene();
}

async function workspaceEvaluate() {
    if (!currentWorkspaceScene) return;

    // Use evaluate-only endpoint (no revision loop)
    const critiqueModel = document.getElementById('ws-critique-model')?.value || undefined;
    const revisionMode = document.querySelector('input[name="ws-revision-mode"]:checked')?.value || 'full';

    // Show modal with loading state
    showEvaluateModal();

    try {
        const response = await fetch(apiUrl(`/scenes/${currentWorkspaceScene.id}/evaluate`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: critiqueModel,
                revision_mode: revisionMode
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to evaluate scene');
        }

        const data = await response.json();
        showEvaluateResult(data);

    } catch (e) {
        hideEvaluateModal();
        showToast('Error', e.message, 'error');
    }
}

// Store last evaluation data for potential revision
let lastEvaluationData = null;

function showEvaluateModal() {
    document.getElementById('evaluate-panel').style.display = 'block';
    document.getElementById('evaluate-loading').style.display = 'flex';
    document.getElementById('evaluate-result').style.display = 'none';
    document.getElementById('evaluate-footer').style.display = 'none';
}

function hideEvaluateModal() {
    document.getElementById('evaluate-panel').style.display = 'none';
    lastEvaluationData = null;
}

function showEvaluateResult(data) {
    lastEvaluationData = data;
    document.getElementById('evaluate-loading').style.display = 'none';
    document.getElementById('evaluate-result').style.display = 'block';
    document.getElementById('evaluate-footer').style.display = 'flex';

    document.getElementById('evaluate-scene-title').textContent = data.title;
    document.getElementById('evaluate-word-count').textContent = `${data.word_count.toLocaleString()} words`;
    document.getElementById('evaluate-mode-badge').textContent = data.revision_mode === 'polish' ? 'Polish' : 'Full';
    document.getElementById('evaluate-critique').textContent = data.critique;
}

async function startRevisionFromEvaluate() {
    if (!currentWorkspaceScene || !lastEvaluationData) return;

    // Save evaluation data before hiding (hideEvaluateModal clears it)
    const evaluationData = lastEvaluationData;
    const revisionMode = evaluationData.revision_mode || 'full';
    const existingCritique = evaluationData.critique;

    // Hide the evaluate panel
    hideEvaluateModal();

    try {
        const generationModel = document.getElementById('ws-generation-model')?.value || undefined;

        // Use the new endpoint that skips critique (uses existing critique from evaluate)
        const response = await fetch(apiUrl(`/generations/start-with-critique`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scene_id: currentWorkspaceScene.id,
                critique: existingCritique,
                generation_model: generationModel,
                revision_mode: revisionMode
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to start revision');
        }

        const data = await response.json();
        workspaceGenId = data.generation_id;
        workspacePreviousProse = currentWorkspaceScene.prose || currentWorkspaceScene.original_prose;

        // Show review state directly (no polling needed - state is already awaiting_approval)
        showWorkspaceReview(data);

        showToast('Success', 'Ready for revision', 'success');
    } catch (e) {
        showToast('Error', e.message, 'error');
        renderWorkspaceView();
    }
}

async function workspaceMarkCanon() {
    if (!currentWorkspaceScene) return;

    const prose = currentWorkspaceScene.prose || currentWorkspaceScene.original_prose;
    if (!prose || !prose.trim()) {
        showToast('Error', 'Cannot mark as canon: scene has no prose content.', 'error');
        return;
    }

    if (!confirm('Mark this scene as canon? Canon scenes are included in the manuscript and used for continuity.')) {
        return;
    }

    try {
        // Send both is_canon and prose to ensure prose is saved to the scene
        const response = await fetch(apiUrl(`/scenes/${currentWorkspaceScene.id}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                is_canon: true,
                prose: prose  // Save prose (may come from original_prose for edit mode scenes)
            })
        });

        if (!response.ok) throw new Error('Failed to mark as canon');

        showToast('Success', 'Scene marked as canon', 'success');

        // Immediately update local state so UI reflects change
        currentWorkspaceScene.is_canon = true;
        currentWorkspaceScene.prose = prose;  // Ensure prose is set locally too

        // Refresh sidebar data
        await loadScenes();
        await loadChapters();

        // Ensure the scenes array has the current scene's prose for word count
        const sceneIndex = scenes.findIndex(s => s.id === currentWorkspaceScene.id);
        if (sceneIndex >= 0) {
            scenes[sceneIndex] = { ...scenes[sceneIndex], ...currentWorkspaceScene };
        }

        updateStats();
        renderOutlineTree();
        renderStructureTree();

        // Re-render workspace with updated state (show ws-canon instead of ws-prose)
        hideAllWorkspaceStates();
        showWorkspaceCanon(currentWorkspaceScene);
        document.getElementById('ws-canon-badge').style.display = 'inline-flex';

    } catch (e) {
        console.error('[Canon Mark] Error:', e);
        showToast('Error', e.message, 'error');
    }
}

async function workspaceRemoveCanon() {
    if (!currentWorkspaceScene) return;

    if (!confirm('Remove this scene from canon? It will no longer be included in the manuscript.')) {
        return;
    }

    try {
        const response = await fetch(apiUrl(`/scenes/${currentWorkspaceScene.id}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_canon: false })
        });

        if (!response.ok) throw new Error('Failed to remove from canon');

        showToast('Success', 'Scene removed from canon', 'success');

        // Immediately update local state so UI reflects change
        currentWorkspaceScene.is_canon = false;

        // Refresh sidebar data
        await loadScenes();
        await loadChapters();

        // Ensure the scenes array has the current scene's updated canon status
        const sceneIndex = scenes.findIndex(s => s.id === currentWorkspaceScene.id);
        if (sceneIndex >= 0) {
            scenes[sceneIndex] = { ...scenes[sceneIndex], ...currentWorkspaceScene };
        }

        updateStats();
        renderOutlineTree();
        renderStructureTree();

        // Re-render workspace with updated state (show ws-prose instead of ws-canon)
        hideAllWorkspaceStates();
        showWorkspaceProse(currentWorkspaceScene);
        document.getElementById('ws-canon-badge').style.display = 'none';

    } catch (e) {
        console.error('[Canon Remove] Error:', e);
        showToast('Error', e.message, 'error');
    }
}

function workspaceEditProse() {
    if (!currentWorkspaceScene) return;

    hideAllWorkspaceStates();

    const prose = currentWorkspaceScene.prose || currentWorkspaceScene.original_prose || '';
    document.getElementById('ws-prose-editor').value = prose;

    const words = prose.trim() ? prose.trim().split(/\s+/).length : 0;
    document.getElementById('ws-editing-word-count').textContent = `${words.toLocaleString()} words`;

    // Track word count changes
    document.getElementById('ws-prose-editor').oninput = function() {
        const w = this.value.trim() ? this.value.trim().split(/\s+/).length : 0;
        document.getElementById('ws-editing-word-count').textContent = `${w.toLocaleString()} words`;
    };

    document.getElementById('ws-editing').style.display = 'block';
}

async function saveWorkspaceProseEdit() {
    if (!currentWorkspaceScene) return;

    const prose = document.getElementById('ws-prose-editor').value;

    try {
        const response = await fetch(apiUrl(`/scenes/${currentWorkspaceScene.id}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prose: prose })
        });

        if (!response.ok) throw new Error('Failed to save prose');

        showToast('Success', 'Prose saved', 'success');
        loadScenes();
        await refreshWorkspaceScene();

    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

function cancelWorkspaceEdit() {
    refreshWorkspaceScene();
}

async function saveWorkspaceProse() {
    // For saving AI revision changes (from floating bubble)
    if (!currentWorkspaceScene) return;

    const prose = document.getElementById('ws-prose-content').textContent;

    try {
        const response = await fetch(apiUrl(`/scenes/${currentWorkspaceScene.id}/save-prose`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prose: prose })
        });

        if (!response.ok) throw new Error('Failed to save prose');

        document.getElementById('ws-dirty-indicator').style.display = 'none';
        showToast('Success', 'Prose saved', 'success');
        loadScenes();

    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function saveWorkspaceReviewProse() {
    // For saving AI revision changes from floating bubble in review state
    if (!currentWorkspaceScene) return;

    const prose = document.getElementById('ws-review-prose').textContent;

    try {
        const response = await fetch(apiUrl(`/scenes/${currentWorkspaceScene.id}/save-prose`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prose: prose })
        });

        if (!response.ok) throw new Error('Failed to save prose');

        document.getElementById('ws-review-dirty-indicator').style.display = 'none';
        showToast('Success', 'Draft saved', 'success');
        loadScenes();

    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

function closeWorkspace() {
    hideAllWorkspaceStates();
    document.getElementById('ws-no-scene').style.display = 'block';
    document.getElementById('ws-title').textContent = 'Select a Scene';
    document.getElementById('ws-subtitle').textContent = '';
    document.getElementById('ws-status-badge').style.display = 'none';
    document.getElementById('ws-canon-badge').style.display = 'none';
    document.getElementById('ws-edit-mode-badge').style.display = 'none';
    currentWorkspaceScene = null;
}

function toggleWorkspaceRevisionInstructions() {
    const body = document.getElementById('ws-revision-instructions-body');
    const toggle = document.getElementById('ws-revision-instructions-toggle');
    const isHidden = body.style.display === 'none';
    body.style.display = isHidden ? 'block' : 'none';
    toggle.textContent = isHidden ? '▼' : '▶';
}

function addWorkspaceRevisionHint(hint) {
    const textarea = document.getElementById('ws-revision-instructions');
    if (textarea.value) {
        textarea.value += '. ' + hint;
    } else {
        textarea.value = hint;
    }
}

function toggleWorkspaceDiff() {
    // Simplified diff toggle for workspace
    const proseEl = document.getElementById('ws-review-prose');
    const diffEl = document.getElementById('ws-review-diff');
    const btn = document.getElementById('ws-diff-toggle-btn');

    if (diffEl.style.display === 'none') {
        diffEl.style.display = 'block';
        proseEl.style.display = 'none';
        btn.textContent = 'Hide Changes';
        // Would need diff computation here
    } else {
        diffEl.style.display = 'none';
        proseEl.style.display = 'block';
        btn.textContent = 'Show Changes';
    }
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
            document.getElementById('gen-preview-outline').value = scene.outline || '';
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
    const revisionMode = document.querySelector('input[name="revision-mode"]:checked')?.value || 'full';

    if (!sceneId) {
        alert('Please select a scene');
        return;
    }

    // Validate models are different if both specified
    if (genModel && critiqueModel && genModel === critiqueModel) {
        alert('Generation and Critique models must be different for effective revision feedback.');
        return;
    }

    // Store models and revision mode for display
    currentGenModel = genModel || 'Default';
    currentCritiqueModel = critiqueModel || 'Default';
    currentRevisionMode = revisionMode;

    try {
        // Save outline changes if modified
        const outlineText = document.getElementById('gen-preview-outline').value;
        const scene = scenes.find(s => s.id === sceneId);
        if (scene && outlineText !== scene.outline) {
            const saveResponse = await fetch(apiUrl(`/scenes/${sceneId}`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ outline: outlineText })
            });
            if (!saveResponse.ok) {
                throw new Error('Failed to save outline changes');
            }
            // Update local scene data
            scene.outline = outlineText;
        }

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
                critique_model: critiqueModel,
                revision_mode: revisionMode
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
        'queued': 'Queued',
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
        'queued': 'Waiting in queue...',
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

    // Show revision mode
    const revisionModeBadge = document.getElementById('revision-mode-badge');
    if (revisionModeBadge) {
        const modeDisplay = (data.revision_mode || currentRevisionMode) === 'polish' ? 'Polish' : 'Full';
        revisionModeBadge.textContent = modeDisplay;
        revisionModeBadge.className = 'badge' + (modeDisplay === 'Polish' ? ' polish-mode' : '');
    }

    // Revise button always enabled (user controls when to stop)
    const reviseBtn = document.getElementById('gen-revise-btn');
    reviseBtn.disabled = false;
    reviseBtn.textContent = 'Approve & Revise';

    // Handle diff view - check if we have a previous iteration
    const diffToggleBtn = document.getElementById('diff-toggle-btn');
    const diffEl = document.getElementById('gen-diff');
    const diffStatsEl = document.getElementById('gen-diff-stats');

    if (data.history && data.history.length > 1) {
        // We have previous iterations - enable diff view
        previousProse = data.history[data.history.length - 2].prose;
        diffToggleBtn.style.display = 'inline-block';

        // Render the diff
        renderDiff(previousProse, data.current_prose || '');

        // Reset to prose view by default
        showingDiff = false;
        diffEl.style.display = 'none';
        document.getElementById('gen-prose').style.display = 'block';
        diffToggleBtn.textContent = 'Show Changes';
        diffStatsEl.style.display = 'none';
    } else {
        // First iteration - hide diff toggle
        previousProse = null;
        diffToggleBtn.style.display = 'none';
        diffEl.style.display = 'none';
        diffStatsEl.style.display = 'none';
        showingDiff = false;
    }
}

// ============================================
// Diff View Functions
// ============================================
function renderDiff(oldText, newText) {
    const diffEl = document.getElementById('gen-diff');
    const diffStatsEl = document.getElementById('gen-diff-stats');

    if (!oldText || !newText) {
        diffEl.innerHTML = '<em class="text-muted">No previous version to compare</em>';
        diffChanges = [];
        return;
    }

    // Store for rebuilding prose later
    diffOldText = oldText;

    // Use jsdiff library (loaded via CDN)
    const diff = Diff.diffWords(oldText, newText);

    let html = '';
    let additions = 0;
    let deletions = 0;
    diffChanges = [];  // Reset changes array
    let changeId = 0;

    diff.forEach(part => {
        if (part.added) {
            additions += part.value.split(/\s+/).filter(w => w).length;
            diffChanges.push({ id: changeId, type: 'add', value: part.value, accepted: true });
            html += `<ins class="diff-add diff-change accepted" data-change-id="${changeId}" onclick="toggleDiffChange(${changeId})">${escapeHtml(part.value)}</ins>`;
            changeId++;
        } else if (part.removed) {
            deletions += part.value.split(/\s+/).filter(w => w).length;
            diffChanges.push({ id: changeId, type: 'del', value: part.value, accepted: true });
            html += `<del class="diff-del diff-change accepted" data-change-id="${changeId}" onclick="toggleDiffChange(${changeId})">${escapeHtml(part.value)}</del>`;
            changeId++;
        } else {
            // Unchanged text - store for rebuilding but no interaction
            diffChanges.push({ id: changeId, type: 'unchanged', value: part.value, accepted: true });
            html += escapeHtml(part.value);
            changeId++;
        }
    });

    // Add actions bar for applying changes
    html += `
        <div class="diff-actions" id="diff-actions">
            <div class="diff-actions-info">
                <span id="diff-changes-count">${additions + deletions} changes</span> -
                Click changes to accept/reject, then apply
            </div>
            <button class="btn btn-success" onclick="applySelectedChanges()">Apply Selected Changes</button>
        </div>
    `;

    diffEl.innerHTML = html;

    // Update stats
    if (additions > 0 || deletions > 0) {
        const statsHtml = [];
        if (additions > 0) statsHtml.push(`<span class="diff-stat-add">+${additions} words</span>`);
        if (deletions > 0) statsHtml.push(`<span class="diff-stat-del">-${deletions} words</span>`);
        diffStatsEl.innerHTML = statsHtml.join(' ');
    }
}

function toggleDiffChange(changeId) {
    const change = diffChanges.find(c => c.id === changeId);
    if (!change || change.type === 'unchanged') return;

    change.accepted = !change.accepted;

    // Update visual state
    const el = document.querySelector(`[data-change-id="${changeId}"]`);
    if (el) {
        el.classList.toggle('accepted', change.accepted);
        el.classList.toggle('rejected', !change.accepted);
    }

    // Update count display
    updateDiffChangesCount();
}

function updateDiffChangesCount() {
    const countEl = document.getElementById('diff-changes-count');
    if (!countEl) return;

    const accepted = diffChanges.filter(c => c.type !== 'unchanged' && c.accepted).length;
    const total = diffChanges.filter(c => c.type !== 'unchanged').length;
    countEl.textContent = `${accepted}/${total} changes accepted`;
}

function buildMergedProse() {
    // Build prose based on accepted/rejected changes
    // - If an 'add' is accepted: include it
    // - If an 'add' is rejected: exclude it
    // - If a 'del' is accepted: exclude the deleted text (keep deletion)
    // - If a 'del' is rejected: include the deleted text (undo deletion)
    // - Unchanged text is always included

    let result = '';

    for (const change of diffChanges) {
        if (change.type === 'unchanged') {
            result += change.value;
        } else if (change.type === 'add') {
            if (change.accepted) {
                result += change.value;  // Include the addition
            }
            // If rejected, don't include it
        } else if (change.type === 'del') {
            if (!change.accepted) {
                result += change.value;  // Undo deletion - include the text
            }
            // If accepted, don't include it (keep it deleted)
        }
    }

    return result;
}

async function applySelectedChanges() {
    const mergedProse = buildMergedProse();

    if (!currentGenId) {
        alert('No active generation to apply changes to.');
        return;
    }

    try {
        // Save to backend
        const response = await fetch(apiUrl(`/generations/${currentGenId}/prose`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prose: mergedProse })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save changes');
        }

        // Update the prose display
        document.getElementById('gen-prose').textContent = mergedProse;

        // Update word count
        const wordCount = mergedProse.split(/\s+/).filter(w => w).length;
        document.getElementById('gen-prose-word-count').textContent = `${wordCount} words`;

        // Switch back to prose view
        showingDiff = false;
        document.getElementById('gen-prose').style.display = 'block';
        document.getElementById('gen-diff').style.display = 'none';
        document.getElementById('diff-toggle-btn').textContent = 'Show Changes';
        document.getElementById('gen-diff-stats').style.display = 'none';

        // Update previousProse for next diff comparison
        previousProse = mergedProse;

        // Clear diff changes
        diffChanges = [];

        alert('Changes applied and saved! You can now Approve & Revise or Accept as Canon.');
    } catch (e) {
        console.error('Error applying changes:', e);
        alert('Error applying changes: ' + e.message);
    }
}

function toggleDiffView() {
    const proseEl = document.getElementById('gen-prose');
    const diffEl = document.getElementById('gen-diff');
    const diffToggleBtn = document.getElementById('diff-toggle-btn');
    const diffStatsEl = document.getElementById('gen-diff-stats');

    showingDiff = !showingDiff;

    if (showingDiff) {
        proseEl.style.display = 'none';
        diffEl.style.display = 'block';
        diffToggleBtn.textContent = 'Show Prose';
        diffStatsEl.style.display = 'inline';
    } else {
        proseEl.style.display = 'block';
        diffEl.style.display = 'none';
        diffToggleBtn.textContent = 'Show Changes';
        diffStatsEl.style.display = 'none';
    }
}

// ============================================
// Revision Instructions Functions
// ============================================
function toggleRevisionInstructions() {
    const body = document.getElementById('revision-instructions-body');
    const toggle = document.getElementById('revision-instructions-toggle');

    if (body.style.display === 'none') {
        body.style.display = 'block';
        toggle.classList.add('open');
    } else {
        body.style.display = 'none';
        toggle.classList.remove('open');
    }
}

function addRevisionHint(hint) {
    const textarea = document.getElementById('revision-instructions');
    const current = textarea.value.trim();

    if (current) {
        textarea.value = current + '. ' + hint;
    } else {
        textarea.value = hint;
    }

    textarea.focus();
}

function clearRevisionInstructions() {
    const textarea = document.getElementById('revision-instructions');
    if (textarea) {
        textarea.value = '';
    }
    // Collapse the section
    const body = document.getElementById('revision-instructions-body');
    const toggle = document.getElementById('revision-instructions-toggle');
    if (body) body.style.display = 'none';
    if (toggle) toggle.classList.remove('open');
}

// ============================================
// Selection-Based Revision Functions
// ============================================
function setupSelectionTracking() {
    const proseEl = document.getElementById('gen-prose');
    if (!proseEl) return;

    // Track selection changes
    document.addEventListener('selectionchange', () => {
        // Only track if we're in the review step
        const reviewStep = document.getElementById('gen-step-review');
        if (!reviewStep || reviewStep.style.display === 'none') return;

        const selection = window.getSelection();
        const selectionInfo = document.getElementById('selection-info');

        // Check if selection is within the prose box
        if (selection.rangeCount > 0 && selection.toString().trim()) {
            const range = selection.getRangeAt(0);
            const proseBox = document.getElementById('gen-prose');

            if (proseBox && proseBox.contains(range.commonAncestorContainer)) {
                const selectedText = selection.toString().trim();

                if (selectedText.length > 0) {
                    // Calculate position within prose text
                    const fullText = proseBox.textContent;
                    const startOffset = getTextOffset(proseBox, range.startContainer, range.startOffset);
                    const endOffset = getTextOffset(proseBox, range.endContainer, range.endOffset);

                    currentSelection = {
                        text: selectedText,
                        start: startOffset,
                        end: endOffset
                    };

                    // Update UI
                    const wordCount = selectedText.split(/\s+/).filter(w => w).length;
                    document.getElementById('selection-word-count').textContent =
                        `${wordCount} word${wordCount !== 1 ? 's' : ''} selected`;
                    selectionInfo.style.display = 'flex';
                    return;
                }
            }
        }

        // No valid selection
        if (currentSelection) {
            currentSelection = null;
            selectionInfo.style.display = 'none';
        }
    });
}

function getTextOffset(root, node, offset) {
    // Calculate the character offset from the start of root to the position
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
    let charCount = 0;

    while (walker.nextNode()) {
        if (walker.currentNode === node) {
            return charCount + offset;
        }
        charCount += walker.currentNode.textContent.length;
    }

    return charCount + offset;
}

function clearSelection() {
    window.getSelection().removeAllRanges();
    currentSelection = null;
    const selectionInfo = document.getElementById('selection-info');
    if (selectionInfo) selectionInfo.style.display = 'none';
}

async function reviseSelection() {
    if (!currentGenId || !currentSelection) return;

    // Get optional instructions
    const instructionsEl = document.getElementById('revision-instructions');
    const instructions = instructionsEl ? instructionsEl.value.trim() : '';

    try {
        document.getElementById('gen-step-review').style.display = 'none';
        document.getElementById('gen-step-progress').style.display = 'block';
        updateProgress('revising', 'Revising selected text...');

        const response = await fetch(apiUrl(`/generations/${currentGenId}/revise-selection`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                selection_start: currentSelection.start,
                selection_end: currentSelection.end,
                selection_text: currentSelection.text,
                instructions: instructions || null
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to revise selection');
        }

        // Clear selection and instructions
        clearSelection();
        clearRevisionInstructions();

        startPolling();
    } catch (e) {
        alert('Error: ' + e.message);
        document.getElementById('gen-step-progress').style.display = 'none';
        document.getElementById('gen-step-review').style.display = 'block';
    }
}

// ============================================
// Floating AI Revision Bubble (Reading View)
// ============================================
let readingSelection = null;  // {text, start, end} for reading view selection

// Helper: Check if element is actually visible (uses computed style)
function isElementVisible(el) {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
}

// Helper: Get the active prose container (workspace or reading view)
function getActiveProseContainer() {
    // Check workspace first
    const workspace = document.getElementById('scene-workspace');
    const wsProseContent = document.getElementById('ws-prose-content');
    const wsProseState = document.getElementById('ws-prose');

    if (workspace && workspace.classList.contains('active') &&
        wsProseState && isElementVisible(wsProseState) && wsProseContent) {

        // Must have a non-canon scene loaded
        if (currentWorkspaceScene && !currentWorkspaceScene.is_canon) {
            return { element: wsProseContent, isWorkspace: true };
        }
    }

    // Also check review state (prose in left column during review)
    const wsReviewState = document.getElementById('ws-review');
    const wsReviewProse = document.getElementById('ws-review-prose');

    if (workspace && workspace.classList.contains('active') &&
        wsReviewState && isElementVisible(wsReviewState) && wsReviewProse) {

        // Review state is always for non-canon scenes
        if (currentWorkspaceScene) {
            return { element: wsReviewProse, isWorkspace: true };
        }
    }

    // Check queue review panel
    const queueView = document.getElementById('queue-view');
    const queueReviewPanel = document.getElementById('queue-review-panel');
    const queueReviewProse = document.getElementById('queue-review-prose');

    if (queueView && queueView.classList.contains('active') &&
        queueReviewPanel && isElementVisible(queueReviewPanel) && queueReviewProse) {

        // Queue review is for generations awaiting approval
        const genId = queueReviewPanel.dataset.genId;
        if (genId) {
            return { element: queueReviewProse, isWorkspace: false, isQueueReview: true, genId: genId };
        }
    }

    // Fall back to reading view (for legacy support)
    const readingView = document.getElementById('reading-view');
    const readingContent = document.getElementById('reading-content');
    const readingMode = document.getElementById('reading-mode');

    if (readingView && readingView.classList.contains('active') &&
        readingContent && readingMode && isElementVisible(readingMode)) {

        // Must be a non-canon scene
        if (currentReadingData && currentReadingData.type === 'scene' && !currentReadingData.is_canon) {
            return { element: readingContent, isWorkspace: false };
        }
    }

    return null;
}

// Handle text selection and show bubble
function handleTextSelection(e) {
    // Skip if we're inside a modal (don't interfere with modal inputs)
    if (e && e.target && e.target.closest('.modal')) {
        return;
    }

    const bubble = document.getElementById('revision-bubble');
    const container = getActiveProseContainer();

    // If clicking inside the bubble, don't process
    if (bubble && e && bubble.contains(e.target)) {
        return;
    }

    // No valid container - hide bubble and return
    if (!container) {
        hideRevisionBubble();
        return;
    }

    const selection = window.getSelection();

    // Check if we have a valid selection
    if (selection.rangeCount > 0 && selection.toString().trim()) {
        const range = selection.getRangeAt(0);

        // Selection must be within our prose container
        if (container.element.contains(range.commonAncestorContainer)) {
            const selectedText = selection.toString().trim();

            // Minimum 10 characters
            if (selectedText.length > 10) {
                const startOffset = getTextOffsetInElement(container.element, range.startContainer, range.startOffset);
                const endOffset = getTextOffsetInElement(container.element, range.endContainer, range.endOffset);

                readingSelection = {
                    text: selectedText,
                    start: startOffset,
                    end: endOffset,
                    isWorkspace: container.isWorkspace,
                    isQueueReview: container.isQueueReview || false,
                    genId: container.genId || null,
                    elementId: container.element.id
                };

                const rect = range.getBoundingClientRect();
                showRevisionBubble(rect);
                return;
            }
        }
    }

    // No valid selection - hide bubble if clicking outside it
    if (e) {
        const isInteractive = e.target.closest('button, a, .btn, .nav-btn, #back-to-top, .revision-bubble');
        if (!isInteractive) {
            hideRevisionBubble();
        }
    }
}

// Handle selection changes (for when selection is cleared)
function handleSelectionChange() {
    // Skip if focus is inside a modal (don't interfere with modal inputs)
    if (document.activeElement && document.activeElement.closest('.modal')) {
        return;
    }

    const selection = window.getSelection();
    const bubble = document.getElementById('revision-bubble');

    // If bubble is visible but selection is now empty, hide it
    // BUT don't hide if focus is inside the bubble (e.g., user clicked in input field)
    if (bubble && bubble.style.display !== 'none') {
        if (!selection.toString().trim()) {
            // Check if active element is inside the bubble
            if (!bubble.contains(document.activeElement)) {
                hideRevisionBubble();
            }
        }
    }
}

function setupReadingSelectionTracking() {
    // Main event: mouseup to detect completed selections
    document.addEventListener('mouseup', handleTextSelection);

    // Selection change: detect when selection is cleared (e.g., clicking elsewhere)
    document.addEventListener('selectionchange', handleSelectionChange);

    // Selection start: hide bubble when starting a new selection
    document.addEventListener('selectstart', (e) => {
        // Skip if we're inside a modal (don't interfere with modal inputs)
        if (e.target && e.target.closest('.modal')) {
            return;
        }

        const bubble = document.getElementById('revision-bubble');
        // Don't process if the selectstart is inside the bubble (e.g., selecting in input)
        if (bubble && bubble.contains(e.target)) {
            return;
        }

        // Small delay to allow the selection to actually start
        setTimeout(() => {
            if (bubble && bubble.style.display !== 'none') {
                // Only hide if we're starting a new selection outside the bubble
                const selection = window.getSelection();
                if (selection.toString().trim().length < 10 && !bubble.contains(document.activeElement)) {
                    hideRevisionBubble();
                }
            }
        }, 50);
    });
}

function getTextOffsetInElement(root, node, offset) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
    let charCount = 0;

    while (walker.nextNode()) {
        if (walker.currentNode === node) {
            return charCount + offset;
        }
        charCount += walker.currentNode.textContent.length;
    }

    return charCount + offset;
}

function showRevisionBubble(selectionRect) {
    const bubble = document.getElementById('revision-bubble');
    if (!bubble) return;

    // Populate model dropdown
    populateBubbleModelSelect();

    // Position bubble near selection
    const bubbleWidth = 280;
    const bubbleHeight = 340;  // Increased for quick action buttons

    let left = selectionRect.left + (selectionRect.width / 2) - (bubbleWidth / 2);
    let top = selectionRect.bottom + 10;

    // Keep within viewport horizontally
    if (left < 10) left = 10;
    if (left + bubbleWidth > window.innerWidth - 10) {
        left = window.innerWidth - bubbleWidth - 10;
    }

    // Keep within viewport vertically
    if (top + bubbleHeight > window.innerHeight - 10) {
        // Try showing above selection
        top = selectionRect.top - bubbleHeight - 10;
    }
    // If still off-screen (above viewport), clamp to top
    if (top < 10) {
        top = 10;
    }

    bubble.style.left = left + 'px';
    bubble.style.top = top + 'px';
    bubble.style.display = 'block';

    // Clear previous instructions
    document.getElementById('bubble-instructions').value = '';
}

function hideRevisionBubble() {
    const bubble = document.getElementById('revision-bubble');
    if (bubble) bubble.style.display = 'none';
    readingSelection = null;
    window.getSelection().removeAllRanges();
}

function populateBubbleModelSelect() {
    const select = document.getElementById('bubble-model-select');
    if (!select) return;

    // Helper to get model display name
    const getModelName = (modelId) => {
        if (!modelId) return 'Not Set';
        const model = availableModels.find(m => m.id === modelId);
        if (model) return model.name;
        const baseId = modelId.replace(/-\d{8}$/, '');
        const partialMatch = availableModels.find(m => m.id.startsWith(baseId) || m.id.includes(baseId.split('/')[1]));
        if (partialMatch) return partialMatch.name;
        return modelId.split('/').pop().replace(/-/g, ' ').replace(/\d{8}$/, '').trim();
    };

    // Default option showing the actual default model
    const defaultName = systemGenModel ? getModelName(systemGenModel) : 'Not Set';
    select.innerHTML = `<option value="">Default Model - ${defaultName}</option>`;

    // Add available models
    if (typeof availableModels !== 'undefined' && availableModels.length > 0) {
        availableModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.name || model.id.split('/').pop();
            select.appendChild(option);
        });
    }
}

async function applyBubbleRevision(quickAction = null) {
    if (!readingSelection) {
        alert('No text selected');
        return;
    }

    // Determine context: workspace, queue review, or old reading view
    const isWorkspace = readingSelection.isWorkspace;
    const isQueueReview = readingSelection.isQueueReview;
    let sceneId;
    let generationId = readingSelection.genId;

    if (isQueueReview) {
        // Queue review - we have genId but need sceneId for context
        const gen = queueData.find(g => g.generation_id === generationId);
        if (!gen) {
            alert('Generation context not found');
            return;
        }
        sceneId = gen.scene_id;
    } else if (isWorkspace) {
        if (!currentWorkspaceScene) {
            alert('No scene context available');
            return;
        }
        sceneId = currentWorkspaceScene.id;
    } else {
        if (!currentReadingData) {
            alert('No scene context available');
            return;
        }
        sceneId = currentReadingData.id;
    }

    if (!sceneId && !generationId) {
        alert('No scene context available');
        return;
    }

    const model = document.getElementById('bubble-model-select').value || null;
    const instructions = document.getElementById('bubble-instructions').value.trim() || null;

    // Check if we're in review state (during generation, prose not saved to scene yet)
    const isReviewState = (currentGenId && document.getElementById('ws-review')?.style.display !== 'none') || isQueueReview;

    // Use the appropriate generation ID
    if (!generationId && isReviewState && currentGenId) {
        generationId = currentGenId;
    }

    // Show loading state on all buttons
    const bubble = document.getElementById('revision-bubble');
    const allBtns = bubble.querySelectorAll('button');
    allBtns.forEach(btn => btn.disabled = true);
    const reviseBtn = bubble.querySelector('.bubble-actions button');
    const originalText = reviseBtn.textContent;
    reviseBtn.textContent = 'Revising...';

    try {
        // Use direct generation endpoint if in review state (synchronous, no new iteration)
        // Otherwise use scene endpoint for saved prose
        const url = isReviewState
            ? apiUrl(`/generations/${generationId}/revise-selection-direct`)
            : apiUrl(`/scenes/${sceneId}/revise-selection`);

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                selection_start: readingSelection.start,
                selection_end: readingSelection.end,
                selection_text: readingSelection.text,
                instructions: instructions,
                model: model,
                quick_action: quickAction
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            let errorDetail = 'Failed to revise selection';
            try {
                const error = JSON.parse(errorText);
                errorDetail = error.detail || errorDetail;
            } catch (e) {
                errorDetail = errorText || errorDetail;
            }
            throw new Error(errorDetail);
        }

        const result = await response.json();

        // Handle different response formats from scene vs generation endpoints
        const mergedProse = result.merged_prose || result.current_prose;
        const wordCount = result.word_count || (mergedProse ? mergedProse.split(/\s+/).filter(w => w).length : 0);

        if (isQueueReview) {
            // Queue review - update the queue review prose element
            const proseElement = document.getElementById('queue-review-prose');
            if (proseElement) {
                proseElement.textContent = mergedProse;
            }

            // Update word count in queue review
            const queueWordCount = document.getElementById('queue-review-word-count');
            if (queueWordCount) {
                queueWordCount.textContent = `${wordCount.toLocaleString()} words`;
            }

            // Update the generation in queueData so it persists
            const gen = queueData.find(g => g.generation_id === generationId);
            if (gen) {
                gen.current_prose = mergedProse;
            }

        } else if (isWorkspace) {
            // Update the correct prose container based on which element was selected from
            const proseElement = document.getElementById(readingSelection.elementId);
            if (proseElement) {
                proseElement.textContent = mergedProse;
            }

            // Update word count - check which stats element is visible
            const proseStats = document.getElementById('ws-prose-stats');
            const reviewWordCount = document.getElementById('ws-review-word-count');
            if (proseStats && isElementVisible(proseStats.parentElement)) {
                proseStats.textContent = `${wordCount.toLocaleString()} words`;
            } else if (reviewWordCount) {
                reviewWordCount.textContent = `${wordCount.toLocaleString()} words`;
            }

            // Update workspace scene data
            currentWorkspaceScene.prose = mergedProse;

            // Show appropriate dirty indicator based on which state we're in
            if (readingSelection.elementId === 'ws-review-prose') {
                document.getElementById('ws-review-dirty-indicator').style.display = 'flex';
            } else {
                document.getElementById('ws-dirty-indicator').style.display = 'flex';
            }

        } else {
            // Old reading view logic
            if (!readingDirty && !readingOriginalProse) {
                readingOriginalProse = currentReadingData.prose;
            }

            readingCurrentProse = mergedProse;
            document.getElementById('reading-content').textContent = mergedProse;
            currentReadingData.prose = mergedProse;
            document.getElementById('reading-stats').textContent = `${wordCount.toLocaleString()} words`;

            setReadingDirty(true);
            autosaveToLocalStorage();
        }

        showToast('Selection Revised', 'Changes pending - remember to save', 'info');
        hideRevisionBubble();

    } catch (e) {
        alert('Error: ' + e.message);
    } finally {
        allBtns.forEach(btn => btn.disabled = false);
        reviseBtn.textContent = originalText;
    }
}

async function applyQuickAction(action) {
    await applyBubbleRevision(action);
}

function setReadingDirty(dirty) {
    readingDirty = dirty;
    const indicator = document.getElementById('reading-dirty-indicator');
    if (indicator) {
        if (dirty) {
            indicator.classList.add('visible');
        } else {
            indicator.classList.remove('visible');
        }
    }
}

function autosaveToLocalStorage() {
    if (!currentReadingData || !readingCurrentProse) return;

    const recoveryData = {
        projectId: currentProject,
        sceneId: currentReadingData.id,
        sceneTitle: currentReadingData.title,
        originalProse: readingOriginalProse,
        currentProse: readingCurrentProse,
        timestamp: Date.now()
    };

    localStorage.setItem('prose_recovery', JSON.stringify(recoveryData));
}

function clearLocalStorageRecovery() {
    localStorage.removeItem('prose_recovery');
}

async function saveReadingProse() {
    if (!currentReadingData || !readingCurrentProse) return;

    const sceneId = currentReadingData.id;
    const saveBtn = document.querySelector('#reading-dirty-indicator .save-btn');

    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';
    }

    try {
        const response = await fetch(apiUrl(`/scenes/${sceneId}/save-prose`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prose: readingCurrentProse })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save');
        }

        const result = await response.json();

        // Clear dirty state
        setReadingDirty(false);
        readingOriginalProse = null;
        readingCurrentProse = null;
        clearLocalStorageRecovery();

        // Reload scenes to update sidebar
        await loadScenes();

        showToast('Saved', result.message, 'success');

    } catch (e) {
        alert('Error saving: ' + e.message);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save';
        }
    }
}

function checkForRecovery() {
    const recoveryJson = localStorage.getItem('prose_recovery');
    if (!recoveryJson) return;

    try {
        const recovery = JSON.parse(recoveryJson);

        // Check if recovery is recent (within 24 hours)
        const hoursSinceRecovery = (Date.now() - recovery.timestamp) / (1000 * 60 * 60);
        if (hoursSinceRecovery > 24) {
            clearLocalStorageRecovery();
            return;
        }

        // Show recovery modal
        const modal = document.getElementById('recovery-modal');
        const info = document.getElementById('recovery-info');
        if (modal && info) {
            const timeAgo = formatTimeAgo(recovery.timestamp);
            info.textContent = `Found unsaved changes to "${recovery.sceneTitle}" from ${timeAgo}.`;
            modal.style.display = 'flex';
        }
    } catch (e) {
        console.error('Error checking recovery:', e);
        clearLocalStorageRecovery();
    }
}

function formatTimeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    return 'yesterday';
}

async function restoreRecovery() {
    const recoveryJson = localStorage.getItem('prose_recovery');
    if (!recoveryJson) return;

    try {
        const recovery = JSON.parse(recoveryJson);

        // Navigate to the scene's project if needed
        if (currentProject !== recovery.projectId) {
            await selectProject(recovery.projectId);
        }

        // Open the scene in reading view
        await showSceneProse(recovery.sceneId);

        // Apply recovered prose
        readingOriginalProse = recovery.originalProse;
        readingCurrentProse = recovery.currentProse;
        document.getElementById('reading-content').textContent = recovery.currentProse;
        currentReadingData.prose = recovery.currentProse;

        // Update word count
        const wordCount = recovery.currentProse.trim().split(/\s+/).length;
        document.getElementById('reading-stats').textContent = `${wordCount.toLocaleString()} words`;

        // Mark as dirty
        setReadingDirty(true);

        showToast('Recovered', 'Unsaved changes restored', 'success');

    } catch (e) {
        console.error('Error restoring recovery:', e);
        alert('Failed to restore changes');
    }

    // Hide modal
    document.getElementById('recovery-modal').style.display = 'none';
}

function discardRecovery() {
    clearLocalStorageRecovery();
    document.getElementById('recovery-modal').style.display = 'none';
    showToast('Discarded', 'Unsaved changes cleared', 'info');
}

function showUnsavedChangesModal(navigationCallback) {
    pendingNavigation = navigationCallback;
    document.getElementById('unsaved-changes-modal').style.display = 'flex';
}

function discardUnsavedChanges() {
    // Clear dirty state
    setReadingDirty(false);
    readingOriginalProse = null;
    readingCurrentProse = null;
    clearLocalStorageRecovery();

    // Hide modal
    document.getElementById('unsaved-changes-modal').style.display = 'none';

    // Execute pending navigation
    if (pendingNavigation) {
        pendingNavigation();
        pendingNavigation = null;
    }
}

async function saveAndContinue() {
    await saveReadingProse();

    // Hide modal
    document.getElementById('unsaved-changes-modal').style.display = 'none';

    // Execute pending navigation
    if (pendingNavigation) {
        pendingNavigation();
        pendingNavigation = null;
    }
}

function checkUnsavedBeforeNavigation(callback) {
    if (readingDirty) {
        showUnsavedChangesModal(callback);
        return false;  // Navigation blocked
    }
    return true;  // OK to navigate
}

async function showCompleteStep(data) {
    document.getElementById('gen-step-progress').style.display = 'none';
    document.getElementById('gen-step-review').style.display = 'none';
    document.getElementById('gen-step-complete').style.display = 'block';

    document.getElementById('gen-summary').textContent = data.scene_summary || 'Summary not generated';

    // Refresh UI to show canon status in sidebar, structure, and dropdown
    await loadAllData();

    // Refresh credits since we just used tokens
    loadCredits();
}

async function approveAndRevise() {
    if (!currentGenId) return;

    try {
        document.getElementById('gen-step-review').style.display = 'none';
        document.getElementById('gen-step-progress').style.display = 'block';
        updateProgress('revising', 'Revising based on critique...');

        // Get revision instructions if provided
        const instructionsEl = document.getElementById('revision-instructions');
        const instructions = instructionsEl ? instructionsEl.value.trim() : '';

        const response = await fetch(apiUrl(`/generations/${currentGenId}/approve`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instructions: instructions || null })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to approve');
        }

        // Clear instructions for next revision
        clearRevisionInstructions();

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
    // Reset manuscript fields
    const manuscriptText = document.getElementById('manuscript-text');
    if (manuscriptText) manuscriptText.value = '';
    const manuscriptFile = document.getElementById('manuscript-file');
    if (manuscriptFile) manuscriptFile.value = '';
    const manuscriptFileName = document.getElementById('manuscript-file-name');
    if (manuscriptFileName) manuscriptFileName.textContent = '';
    importPreviewData = null;
    manuscriptPreviewData = null;
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

    // Show/hide appropriate sections
    const importFileSection = document.getElementById('import-file-section');
    const importTextSection = document.getElementById('import-text-section');
    const manuscriptFileSection = document.getElementById('manuscript-file-section');
    const manuscriptTextSection = document.getElementById('manuscript-text-section');

    // Default: show outline/characters sections, hide manuscript sections
    importFileSection.style.display = type === 'manuscript' ? 'none' : 'block';
    importTextSection.style.display = type === 'manuscript' ? 'none' : 'block';
    manuscriptFileSection.style.display = type === 'manuscript' ? 'block' : 'none';
    manuscriptTextSection.style.display = type === 'manuscript' ? 'block' : 'none';

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
    } else if (type === 'manuscript') {
        helpText.textContent = 'Upload a manuscript file (.docx, .txt, .md) or paste text. Scenes will be created in edit mode for critique/revision.';
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
    } else if (currentImportType === 'manuscript') {
        previewManuscriptImport();
    }
}

function confirmImport() {
    if (currentImportType === 'outline') {
        confirmOutlineImport();
    } else if (currentImportType === 'characters') {
        confirmCharactersImport();
    } else if (currentImportType === 'manuscript') {
        confirmManuscriptImport();
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
    // Reset all preview types
    document.getElementById('import-outline-preview').style.display = 'none';
    document.getElementById('import-characters-preview').style.display = 'none';
    document.getElementById('import-manuscript-preview').style.display = 'none';
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
// Manuscript Import Functions
// ============================================

// Store manuscript data between preview and confirm
let manuscriptPreviewData = null;

async function handleManuscriptFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const validTypes = ['.docx', '.txt', '.md', '.markdown'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validTypes.includes(ext)) {
        alert('Please upload a .docx, .txt, or .md file');
        event.target.value = '';
        return;
    }

    document.getElementById('manuscript-file-name').textContent = `Loading: ${file.name}...`;

    // For .docx files, we need to upload to the server for conversion
    if (ext === '.docx') {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(apiUrl('/manuscript/upload'), {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to upload file');
            }

            const result = await response.json();
            document.getElementById('manuscript-text').value = result.full_text;
            document.getElementById('manuscript-file-name').textContent = `Loaded: ${file.name} (${result.total_words} words)`;
        } catch (e) {
            alert('Error uploading .docx file: ' + e.message);
            document.getElementById('manuscript-file-name').textContent = '';
            event.target.value = '';
        }
    } else {
        // For text files, read directly
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('manuscript-text').value = e.target.result;
            const wordCount = e.target.result.split(/\s+/).filter(w => w.length > 0).length;
            document.getElementById('manuscript-file-name').textContent = `Loaded: ${file.name} (${wordCount} words)`;
        };
        reader.onerror = function() {
            alert('Error reading file');
            document.getElementById('manuscript-file-name').textContent = '';
        };
        reader.readAsText(file);
    }
}

async function previewManuscriptImport() {
    const text = document.getElementById('manuscript-text').value.trim();

    if (!text) {
        alert('Please upload a file or paste manuscript text');
        return;
    }

    if (text.length < 100) {
        alert('Text is too short. Please provide more content.');
        return;
    }

    // Show progress
    document.getElementById('import-step-input').style.display = 'none';
    document.getElementById('import-step-progress').style.display = 'block';

    try {
        // Call the split endpoint
        const formData = new FormData();
        formData.append('text', text);

        const response = await fetch(apiUrl('/manuscript/split'), {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to analyze manuscript');
        }

        const result = await response.json();

        // Store for later
        manuscriptPreviewData = {
            chapters: result.chapters,
            totalWords: result.total_words,
            fullText: text
        };

        // Update preview UI
        document.getElementById('manuscript-filename').textContent =
            document.getElementById('manuscript-file-name').textContent.replace('Loaded: ', '') || 'Pasted text';
        document.getElementById('manuscript-wordcount').textContent = result.total_words.toLocaleString();
        document.getElementById('manuscript-chapter-count').textContent = result.total_chapters;

        // Populate act dropdown
        const actSelect = document.getElementById('manuscript-target-act');
        actSelect.innerHTML = '<option value="">-- No Act (standalone chapters) --</option>';
        acts.forEach(act => {
            actSelect.innerHTML += `<option value="${act.id}">${act.title}</option>`;
        });

        // Render chapter list
        const chaptersList = document.getElementById('manuscript-chapters-list');
        chaptersList.innerHTML = result.chapters.map((ch, i) => `
            <div class="manuscript-chapter-item">
                <span class="chapter-title">${ch.title}</span>
                <span class="chapter-words">${ch.word_count.toLocaleString()} words</span>
            </div>
        `).join('');

        // Set up checkbox listener
        const splitCheckbox = document.getElementById('manuscript-split-chapters');
        splitCheckbox.onchange = function() {
            document.getElementById('manuscript-chapters-list').style.display = this.checked ? 'block' : 'none';
            document.getElementById('manuscript-single-scene').style.display = this.checked ? 'none' : 'block';
            if (!this.checked) {
                document.getElementById('manuscript-preview-content').textContent = text.substring(0, 500) + '...';
            }
        };

        // Show preview
        document.getElementById('import-step-progress').style.display = 'none';
        document.getElementById('import-step-preview').style.display = 'block';

        // Hide other preview types, show manuscript
        document.getElementById('import-outline-preview').style.display = 'none';
        document.getElementById('import-characters-preview').style.display = 'none';
        document.getElementById('import-manuscript-preview').style.display = 'block';

    } catch (e) {
        document.getElementById('import-step-progress').style.display = 'none';
        document.getElementById('import-step-input').style.display = 'block';
        alert('Error analyzing manuscript: ' + e.message);
    }
}

async function confirmManuscriptImport() {
    const actId = document.getElementById('manuscript-target-act').value;
    const splitByChapters = document.getElementById('manuscript-split-chapters').checked;

    // Show progress
    document.getElementById('import-step-preview').style.display = 'none';
    document.getElementById('import-step-progress').style.display = 'block';

    try {
        let result;

        if (splitByChapters) {
            // Validate manuscript data exists
            if (!manuscriptPreviewData || !manuscriptPreviewData.chapters) {
                throw new Error('No manuscript data available. Please preview first.');
            }
            if (!Array.isArray(manuscriptPreviewData.chapters) || manuscriptPreviewData.chapters.length === 0) {
                throw new Error('No chapters found in manuscript data.');
            }

            // Bulk import - create chapters and scenes
            const response = await fetch(apiUrl('/manuscript/import-bulk'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chapters: manuscriptPreviewData.chapters,
                    act_id: actId || null,
                    enable_edit_mode: true,
                    create_chapters: true
                })
            });

            if (!response.ok) {
                const error = await response.json();
                console.error('Import bulk error:', error);
                // Handle FastAPI validation errors (detail is an array)
                let errorMsg = 'Failed to import manuscript';
                if (Array.isArray(error.detail)) {
                    errorMsg = error.detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join('; ');
                } else if (typeof error.detail === 'string') {
                    errorMsg = error.detail;
                }
                throw new Error(errorMsg);
            }

            result = await response.json();
            document.getElementById('import-result-message').textContent =
                `Created ${result.chapters_created} chapters and ${result.scenes_created} scenes with ${result.total_words.toLocaleString()} words in edit mode.`;
        } else {
            // Single chapter/scene import - create one chapter with one scene
            const sceneTitle = document.getElementById('manuscript-scene-title').value.trim() || 'Imported Manuscript';

            // Use bulk import with single chapter
            const response = await fetch(apiUrl('/manuscript/import-bulk'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chapters: [{
                        chapter_number: 1,
                        title: sceneTitle,
                        content: manuscriptPreviewData.fullText,
                        word_count: manuscriptPreviewData.totalWords
                    }],
                    act_id: actId || null,
                    enable_edit_mode: true,
                    create_chapters: true
                })
            });

            if (!response.ok) {
                const error = await response.json();
                console.error('Import bulk error:', error);
                let errorMsg = 'Failed to import manuscript';
                if (Array.isArray(error.detail)) {
                    errorMsg = error.detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join('; ');
                } else if (typeof error.detail === 'string') {
                    errorMsg = error.detail;
                }
                throw new Error(errorMsg);
            }

            result = await response.json();
            document.getElementById('import-result-message').textContent =
                `Created chapter "${sceneTitle}" with ${result.total_words.toLocaleString()} words in edit mode.`;
        }

        // Show complete step
        document.getElementById('import-step-progress').style.display = 'none';
        document.getElementById('import-step-complete').style.display = 'block';

        // Refresh data after import
        await loadChapters();
        await loadScenes();

        // Auto-close modal after brief delay
        setTimeout(() => {
            hideImportOutlineModal();
            switchView('structure');
        }, 1500);

    } catch (e) {
        document.getElementById('import-step-progress').style.display = 'none';
        document.getElementById('import-step-preview').style.display = 'block';
        alert('Error importing manuscript: ' + e.message);
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
        const canDelete = ['completed', 'rejected', 'error'].includes(gen.status);

        return `
            <div class="queue-item">
                <div class="queue-item-info" onclick="openQueueReview('${gen.generation_id}')">
                    <div class="queue-item-title">${escapeHtml(sceneTitle)}</div>
                    <div class="queue-item-meta">
                        <span>Iteration ${gen.current_iteration}</span>
                        <span>${formatRelativeTime(gen.updated_at)}</span>
                    </div>
                </div>
                <div class="queue-item-actions">
                    <span class="queue-status-badge ${gen.status}">${statusLabel}</span>
                    ${canDelete ? `<button class="btn btn-danger btn-xs" onclick="deleteQueueItem('${gen.generation_id}', event)" title="Delete">×</button>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

async function deleteQueueItem(generationId, event) {
    event.stopPropagation();

    try {
        const response = await fetch(apiUrl(`/generations/${generationId}`), {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete');

        await loadQueue();
        showToast('Deleted', 'Generation removed from queue', 'success');
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function clearCompletedQueue() {
    const finishedStatuses = ['completed', 'rejected', 'error'];
    const toDelete = queueData.filter(g => finishedStatuses.includes(g.status));

    if (toDelete.length === 0) {
        showToast('Nothing to Clear', 'No completed/rejected/failed items in queue', 'info');
        return;
    }

    if (!confirm(`Delete ${toDelete.length} finished generation(s)?`)) return;

    let deleted = 0;
    for (const gen of toDelete) {
        try {
            const response = await fetch(apiUrl(`/generations/${gen.generation_id}`), {
                method: 'DELETE'
            });
            if (response.ok) deleted++;
        } catch (e) {
            console.error('Failed to delete', gen.generation_id, e);
        }
    }

    await loadQueue();
    showToast('Cleared', `Removed ${deleted} item(s) from queue`, 'success');
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

    if (selectedScenes.size > 0) {
        if (!controls) {
            // Create batch controls if they don't exist
            const sidebar = document.getElementById('sidebar');
            const footer = sidebar?.querySelector('.sidebar-footer');

            if (!footer) {
                console.error('sidebar-footer not found');
                return;
            }

            const batchDiv = document.createElement('div');
            batchDiv.id = 'batch-controls';
            batchDiv.className = 'batch-controls';
            batchDiv.innerHTML = `
                <span class="batch-count" id="batch-count">${selectedScenes.size} selected</span>
                <button class="btn btn-success btn-sm" onclick="startBatchGeneration()">Generate Selected</button>
                <button class="btn btn-secondary btn-sm" onclick="clearSelection()">Clear</button>
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
    if (selectedScenes.size === 0) {
        alert('No scenes selected');
        return;
    }

    const sceneIds = Array.from(selectedScenes);

    // Load current queue to check for conflicts
    await loadQueue();

    // Check for conflicts - scenes with active generations
    const activeStatuses = ['queued', 'initialized', 'generating', 'critiquing', 'revising',
                           'generation_complete', 'awaiting_approval', 'generating_summary'];

    const conflicts = [];
    const readyToGenerate = [];

    for (const sceneId of sceneIds) {
        const activeGen = queueData.find(g => g.scene_id === sceneId && activeStatuses.includes(g.status));
        if (activeGen) {
            const scene = scenes.find(s => s.id === sceneId);
            conflicts.push({
                sceneId,
                sceneTitle: scene ? scene.title : sceneId,
                status: activeGen.status,
                generationId: activeGen.generation_id
            });
        } else {
            readyToGenerate.push(sceneId);
        }
    }

    // Handle conflicts
    if (conflicts.length > 0) {
        const conflictList = conflicts.map(c => `• ${c.sceneTitle} (${c.status})`).join('\n');
        const message = conflicts.length === sceneIds.length
            ? `All selected scenes already have active generations:\n\n${conflictList}\n\nWould you like to open the Queue to review them?`
            : `${conflicts.length} scene(s) already have active generations:\n\n${conflictList}\n\nGenerate the other ${readyToGenerate.length} scene(s)?`;

        if (conflicts.length === sceneIds.length) {
            if (confirm(message)) {
                clearSelection();
                navigateToView('queue');
            }
            return;
        }

        if (!confirm(message)) {
            return;
        }
    }

    if (readyToGenerate.length === 0) {
        showToast('Nothing to Generate', 'All selected scenes already have active generations.', 'info');
        return;
    }

    const total = readyToGenerate.length;

    // Clear selection and switch to queue view immediately
    clearSelection();
    navigateToView('queue');

    // STEP 1: Queue all scenes first (they appear immediately with "Queued" status)
    showToast('Queuing', `Adding ${total} scene(s) to queue...`, 'info');

    const queuedGenerations = [];

    for (const sceneId of readyToGenerate) {
        const scene = scenes.find(s => s.id === sceneId);
        const sceneTitle = scene ? scene.title : sceneId;

        try {
            // Cleanup old completed/rejected/error generations for this scene first
            await fetch(apiUrl(`/generations/by-scene/${sceneId}?keep_active=true`), {
                method: 'DELETE'
            });

            // Queue the scene (creates QUEUED state)
            const response = await fetch(apiUrl('/generations/queue'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    scene_id: sceneId,
                    max_iterations: 5
                })
            });

            if (response.ok) {
                const data = await response.json();
                queuedGenerations.push({
                    generationId: data.generation_id,
                    sceneId,
                    sceneTitle
                });
            } else {
                const errorData = await response.json();
                console.error('Queue failed:', errorData);
                showToast('Failed to Queue', `${sceneTitle}: ${errorData.detail || 'Unknown error'}`, 'error');
            }
        } catch (e) {
            console.error('Error queuing', sceneId, e);
            showToast('Error', `${sceneTitle}: ${e.message}`, 'error');
        }
    }

    // Refresh queue to show all queued items
    await loadQueue();

    if (queuedGenerations.length === 0) {
        showToast('Queue Failed', 'No scenes were queued successfully.', 'error');
        return;
    }

    showToast('Queued', `${queuedGenerations.length} scene(s) queued. Starting generation...`, 'success');

    // STEP 2: Process queued generations one at a time
    let completed = 0;
    let failed = 0;

    for (let i = 0; i < queuedGenerations.length; i++) {
        const { generationId, sceneTitle } = queuedGenerations[i];

        try {
            showToast('Generating', `${sceneTitle} (${i + 1}/${queuedGenerations.length})`, 'info');

            // Start this queued generation
            const response = await fetch(apiUrl(`/generations/${generationId}/start-queued`), {
                method: 'POST'
            });

            if (response.ok) {
                // Poll until this generation reaches awaiting_approval, completed, or error
                await waitForGeneration(generationId);
                completed++;
            } else {
                const errorData = await response.json();
                console.error('Start failed:', errorData);
                failed++;
                showToast('Failed', `${sceneTitle}: ${errorData.detail || 'Unknown error'}`, 'error');
            }
        } catch (e) {
            failed++;
            console.error('Error starting generation for', sceneTitle, e);
            showToast('Error', `${sceneTitle}: ${e.message}`, 'error');
        }

        // Update queue view after each
        await loadQueue();
    }

    showToast('Batch Complete', `${completed} ready for review, ${failed} failed.`, completed > 0 ? 'success' : 'error');
}

async function waitForGeneration(generationId) {
    // Poll until generation reaches a stopping point
    const maxWait = 300000; // 5 minutes max per scene
    const pollInterval = 2000;
    const startTime = Date.now();

    while (Date.now() - startTime < maxWait) {
        try {
            const response = await fetch(apiUrl(`/generations/${generationId}`));
            if (!response.ok) break;

            const data = await response.json();

            // Stop polling when generation reaches a terminal or review state
            if (['awaiting_approval', 'completed', 'error', 'rejected'].includes(data.status)) {
                return data;
            }

            await new Promise(resolve => setTimeout(resolve, pollInterval));
        } catch (e) {
            console.error('Error polling generation:', e);
            break;
        }
    }

    return null;
}

async function generateChapter(chapterId, event) {
    event.stopPropagation();

    const chapterScenes = scenes.filter(s => s.chapter_id === chapterId && !s.is_canon);
    if (chapterScenes.length === 0) {
        alert('No non-canon scenes in this chapter');
        return;
    }

    // Select these scenes and use the batch generation flow
    chapterScenes.forEach(s => selectedScenes.add(s.id));
    updateBatchControls();
    renderOutlineTree();

    // Now trigger batch generation which handles conflicts
    await startBatchGeneration();
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

// ============================================
// OpenRouter Credits
// ============================================
async function loadCredits() {
    const valueEl = document.getElementById('credits-remaining');
    if (!valueEl) return;

    try {
        const response = await fetch('/api/settings/credits');
        if (!response.ok) {
            if (response.status === 400) {
                // No API key configured
                valueEl.textContent = '--';
                valueEl.className = 'credits-value';
                return;
            }
            throw new Error('Failed to fetch credits');
        }

        const data = await response.json();
        const remaining = data.remaining;

        // Format the display value
        if (remaining >= 1) {
            valueEl.textContent = '$' + remaining.toFixed(2);
        } else {
            valueEl.textContent = '$' + remaining.toFixed(3);
        }

        // Color based on threshold or fixed amounts
        valueEl.className = 'credits-value';
        const threshold = creditAlertSettings.threshold || 5;
        if (remaining < 1) {
            valueEl.classList.add('critical');
        } else if (remaining < threshold) {
            valueEl.classList.add('low');
        }

        // Show alert if enabled and below threshold (max once per 10 minutes)
        const now = Date.now();
        if (creditAlertSettings.enabled && remaining < threshold && (now - lastCreditAlertShown > 600000)) {
            lastCreditAlertShown = now;
            showToast('Low Credits', `Balance is $${remaining.toFixed(2)} - consider topping up`, 'warning');
        }

    } catch (e) {
        console.error('Failed to load credits:', e);
        valueEl.textContent = '--';
        valueEl.className = 'credits-value';
    }
}

async function refreshCredits() {
    const valueEl = document.getElementById('credits-remaining');
    if (valueEl) {
        valueEl.textContent = '...';
    }
    await loadCredits();
    showToast('Credits', 'Balance refreshed', 'success');
}

// ============================================
// Backup System
// ============================================
async function loadBackups() {
    if (!currentProject) return;

    await Promise.all([
        loadSnapshots(),
        populateBackupSceneSelect()
    ]);
}

async function loadSnapshots() {
    const listEl = document.getElementById('snapshots-list');
    const statEl = document.getElementById('backup-stat-snapshots');

    listEl.innerHTML = '<div class="empty-state">Loading snapshots...</div>';

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/backups/snapshots`);
        if (!response.ok) throw new Error('Failed to fetch snapshots');

        const snapshots = await response.json();

        statEl.textContent = snapshots.length;

        if (snapshots.length === 0) {
            listEl.innerHTML = '<div class="empty-state">No project snapshots yet. Create a checkpoint to save your current progress.</div>';
            return;
        }

        listEl.innerHTML = snapshots.map(snapshot => `
            <div class="backup-item">
                <div class="backup-item-info">
                    <div class="backup-item-title">${escapeHtml(snapshot.name)}</div>
                    <div class="backup-item-meta">
                        ${formatRelativeTime(snapshot.timestamp)} ·
                        ${snapshot.scene_count} scene${snapshot.scene_count !== 1 ? 's' : ''} ·
                        <span class="backup-reason ${snapshot.reason === 'checkpoint' ? 'checkpoint' : ''}">${snapshot.reason}</span>
                    </div>
                </div>
                <button class="btn btn-small" onclick="restoreSnapshot('${escapeHtml(snapshot.directory)}')">Restore</button>
            </div>
        `).join('');

    } catch (e) {
        console.error('Failed to load snapshots:', e);
        listEl.innerHTML = '<div class="empty-state error">Failed to load snapshots</div>';
    }
}

async function populateBackupSceneSelect() {
    const selectEl = document.getElementById('backup-scene-select');
    const versionsListEl = document.getElementById('scene-versions-list');

    selectEl.innerHTML = '<option value="">-- Select a Scene --</option>';
    versionsListEl.style.display = 'none';

    if (!scenes || scenes.length === 0) {
        return;
    }

    // Build scene options grouped by chapter
    const scenesByChapter = {};
    scenes.forEach(scene => {
        const chapterId = scene.chapter_id || 'uncategorized';
        if (!scenesByChapter[chapterId]) {
            scenesByChapter[chapterId] = [];
        }
        scenesByChapter[chapterId].push(scene);
    });

    // Add options
    for (const [chapterId, chapterScenes] of Object.entries(scenesByChapter)) {
        const chapter = chapters.find(c => c.id === chapterId);
        const chapterName = chapter ? chapter.title : 'Uncategorized';

        const optgroup = document.createElement('optgroup');
        optgroup.label = chapterName;

        for (const scene of chapterScenes) {
            const option = document.createElement('option');
            option.value = scene.id;
            option.textContent = scene.title || `Scene ${scene.scene_number || '?'}`;
            optgroup.appendChild(option);
        }

        selectEl.appendChild(optgroup);
    }

    // Fetch backup stats for each scene (in background)
    fetchBackupStats();
}

async function fetchBackupStats() {
    const statScenesEl = document.getElementById('backup-stat-scenes');
    const statVersionsEl = document.getElementById('backup-stat-versions');

    let scenesWithBackups = 0;
    let totalVersions = 0;

    // Check each scene for backups
    for (const scene of scenes) {
        try {
            const response = await fetch(`/api/projects/${currentProject.id}/backups/scenes/${scene.id}/versions`);
            if (response.ok) {
                const versions = await response.json();
                if (versions.length > 0) {
                    scenesWithBackups++;
                    totalVersions += versions.length;
                }
            }
        } catch (e) {
            // Ignore individual failures
        }
    }

    statScenesEl.textContent = scenesWithBackups;
    statVersionsEl.textContent = totalVersions;
}

async function loadSceneVersions() {
    const selectEl = document.getElementById('backup-scene-select');
    const listEl = document.getElementById('scene-versions-list');
    const sceneId = selectEl.value;

    if (!sceneId) {
        listEl.style.display = 'none';
        return;
    }

    listEl.style.display = 'block';
    listEl.innerHTML = '<div class="empty-state">Loading versions...</div>';

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/backups/scenes/${sceneId}/versions`);
        if (!response.ok) throw new Error('Failed to fetch versions');

        const versions = await response.json();

        if (versions.length === 0) {
            listEl.innerHTML = '<div class="empty-state">No backups for this scene yet.</div>';
            return;
        }

        listEl.innerHTML = versions.map(version => `
            <div class="backup-item">
                <div class="backup-item-info">
                    <div class="backup-item-title">${formatRelativeTime(version.timestamp)}</div>
                    <div class="backup-item-meta">
                        ${version.word_count} words ·
                        ${version.is_canon ? '<span class="badge canon">Canon</span>' : '<span class="badge">Draft</span>'} ·
                        <span class="backup-reason">${version.reason}</span>
                    </div>
                </div>
                <button class="btn btn-small" onclick="restoreSceneVersion('${sceneId}', '${escapeHtml(version.filename)}')">Restore</button>
            </div>
        `).join('');

    } catch (e) {
        console.error('Failed to load scene versions:', e);
        listEl.innerHTML = '<div class="empty-state error">Failed to load versions</div>';
    }
}

async function createCheckpoint() {
    const name = prompt('Enter a name for this checkpoint:');
    if (!name || !name.trim()) return;

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/backups/checkpoint`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name.trim() })
        });

        if (!response.ok) throw new Error('Failed to create checkpoint');

        showToast('Checkpoint Created', `Saved checkpoint "${name.trim()}"`, 'success');
        await loadSnapshots();

    } catch (e) {
        console.error('Failed to create checkpoint:', e);
        showToast('Error', 'Failed to create checkpoint', 'error');
    }
}

async function restoreSnapshot(directory) {
    if (!confirm('Are you sure you want to restore this snapshot? This will overwrite your current project state. A backup will be created first.')) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/backups/snapshots/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version: directory })
        });

        if (!response.ok) throw new Error('Failed to restore snapshot');

        showToast('Snapshot Restored', 'Project restored from snapshot. Reloading...', 'success');

        // Reload all project data
        setTimeout(async () => {
            await loadAllData();
            await loadBackups();
        }, 500);

    } catch (e) {
        console.error('Failed to restore snapshot:', e);
        showToast('Error', 'Failed to restore snapshot', 'error');
    }
}

async function restoreSceneVersion(sceneId, filename) {
    if (!confirm('Are you sure you want to restore this version? The current scene content will be backed up first.')) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${currentProject.id}/backups/scenes/${sceneId}/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version: filename })
        });

        if (!response.ok) throw new Error('Failed to restore scene version');

        showToast('Scene Restored', 'Scene restored from backup', 'success');

        // Reload scenes and refresh the version list
        await loadScenes();
        await loadSceneVersions();

    } catch (e) {
        console.error('Failed to restore scene version:', e);
        showToast('Error', 'Failed to restore scene version', 'error');
    }
}
