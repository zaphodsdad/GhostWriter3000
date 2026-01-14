// Main application JavaScript

// View navigation
document.addEventListener('DOMContentLoaded', () => {
    // Initialize navigation
    const navButtons = document.querySelectorAll('.nav-btn');
    const views = document.querySelectorAll('.view');

    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const viewName = button.dataset.view;
            if (!viewName) return; // Skip buttons without data-view (like Generate)

            // Update active button
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Update active view
            views.forEach(view => view.classList.remove('active'));
            const targetView = document.getElementById(`${viewName}-view`);
            if (targetView) {
                targetView.classList.add('active');
            }
        });
    });

    // Check API health
    checkAPIHealth();

    // Load dynamic data
    loadCharacters();
    loadWorldContexts();
    loadScenes();
    loadStats();

    // Set up auto-refresh for health check
    setInterval(checkAPIHealth, 30000); // Check every 30 seconds
});

// Load and display characters from API
async function loadCharacters() {
    try {
        const response = await fetch('/api/characters/');
        const characters = await response.json();
        const container = document.getElementById('characters-view');
        if (!container) return;

        let html = '<h2>Characters</h2>';

        if (characters.length === 0) {
            html += '<div class="info-card"><p>No characters yet. Create one to get started!</p></div>';
        } else {
            characters.forEach(char => {
                const meta = char.metadata || {};
                html += `
                    <div class="info-card">
                        <h3>${meta.name || char.id}</h3>
                        <div class="metadata">
                            ${meta.role ? `<span class="badge">${meta.role}</span>` : ''}
                            ${meta.age ? `<span class="badge">Age: ${meta.age}</span>` : ''}
                            ${meta.occupation ? `<span class="badge">${meta.occupation}</span>` : ''}
                        </div>
                        ${meta.personality_traits ? `<p><strong>Personality:</strong> ${meta.personality_traits.join(', ')}</p>` : ''}
                        ${meta.background ? `<p><strong>Background:</strong> ${meta.background}</p>` : ''}
                        <details>
                            <summary>View Full Profile</summary>
                            <div class="full-content" style="white-space: pre-wrap;">${char.content || 'No additional content'}</div>
                        </details>
                    </div>
                `;
            });
        }

        html += '<button class="btn-primary">+ Add New Character</button>';
        container.innerHTML = html;
        document.getElementById('char-count').textContent = characters.length;
    } catch (error) {
        console.error('Failed to load characters:', error);
    }
}

// Load and display world contexts from API
async function loadWorldContexts() {
    try {
        const response = await fetch('/api/world/');
        const worlds = await response.json();
        const container = document.getElementById('world-view');
        if (!container) return;

        let html = '<h2>World Context</h2>';

        if (worlds.length === 0) {
            html += '<div class="info-card"><p>No world contexts yet. Create one to get started!</p></div>';
        } else {
            worlds.forEach(world => {
                const meta = world.metadata || {};
                html += `
                    <div class="info-card">
                        <h3>${meta.name || world.id}</h3>
                        <div class="metadata">
                            ${meta.era ? `<span class="badge">${meta.era}</span>` : ''}
                            ${meta.technology_level ? `<span class="badge">${meta.technology_level}</span>` : ''}
                            ${meta.magic_system ? `<span class="badge">${meta.magic_system}</span>` : ''}
                        </div>
                        <details>
                            <summary>View Full Context</summary>
                            <div class="full-content" style="white-space: pre-wrap;">${world.content || 'No additional content'}</div>
                        </details>
                    </div>
                `;
            });
        }

        html += '<button class="btn-primary">+ Add New World Context</button>';
        container.innerHTML = html;
        document.getElementById('world-count').textContent = worlds.length;
    } catch (error) {
        console.error('Failed to load world contexts:', error);
    }
}

// Load and display scenes from API
async function loadScenes() {
    try {
        const response = await fetch('/api/scenes/');
        const scenes = await response.json();
        const container = document.getElementById('scenes-view');
        if (!container) return;

        let html = '<h2>Scenes</h2>';

        if (scenes.length === 0) {
            html += '<div class="info-card"><p>No scenes yet. Create one to get started!</p></div>';
        } else {
            scenes.forEach(scene => {
                const canonBadge = scene.is_canon ? '<span class="badge" style="background: var(--success);">Canon</span>' : '';
                html += `
                    <div class="info-card">
                        <h3>${scene.title}</h3>
                        <div class="metadata">
                            <span class="badge">${scene.id}</span>
                            ${canonBadge}
                            ${scene.tone ? `<span class="badge">${scene.tone}</span>` : ''}
                        </div>
                        <p><strong>Outline:</strong> ${scene.outline.substring(0, 200)}${scene.outline.length > 200 ? '...' : ''}</p>
                        <details>
                            <summary>View Scene Details</summary>
                            <div class="full-content">
                                <p><strong>Full Outline:</strong> ${scene.outline}</p>
                                ${scene.pov ? `<p><strong>POV:</strong> ${scene.pov}</p>` : ''}
                                ${scene.target_length ? `<p><strong>Target Length:</strong> ${scene.target_length}</p>` : ''}
                                ${scene.additional_notes ? `<p><strong>Notes:</strong> ${scene.additional_notes}</p>` : ''}
                                ${scene.prose ? `<p><strong>Prose:</strong></p><div style="white-space: pre-wrap; background: var(--background); padding: 10px; border-radius: 4px; max-height: 300px; overflow-y: auto;">${scene.prose}</div>` : ''}
                                ${scene.summary ? `<p><strong>Summary:</strong> ${scene.summary}</p>` : ''}
                            </div>
                        </details>
                        ${!scene.is_canon ? '<button class="btn-success">Generate Prose</button>' : '<span style="color: var(--success);">✓ Prose Complete</span>'}
                    </div>
                `;
            });
        }

        html += '<button class="btn-primary">+ Add New Scene</button>';
        container.innerHTML = html;
        document.getElementById('scene-count').textContent = scenes.length;
    } catch (error) {
        console.error('Failed to load scenes:', error);
    }
}

// Load stats
async function loadStats() {
    try {
        const genResponse = await fetch('/api/generations/');
        const generations = await genResponse.json();
        document.getElementById('gen-count').textContent = generations.length;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Check API health endpoint
async function checkAPIHealth() {
    const apiStatus = document.getElementById('api-status');
    const backendStatus = document.getElementById('backend-status');

    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        if (response.ok && data.status === 'healthy') {
            apiStatus.textContent = 'Online';
            apiStatus.className = 'status-badge online';
            backendStatus.textContent = `Connected (v${data.version})`;
            backendStatus.className = 'status-badge online';
        } else {
            throw new Error('Unhealthy response');
        }
    } catch (error) {
        apiStatus.textContent = 'Offline';
        apiStatus.className = 'status-badge offline';
        backendStatus.textContent = 'Not Connected';
        backendStatus.className = 'status-badge offline';
    }
}

// Button click handlers (using event delegation for dynamically added buttons)
document.addEventListener('click', (e) => {
    const target = e.target;

    // "Generate Prose" buttons - go to create page
    if (target.classList.contains('btn-success')) {
        const text = target.textContent || '';
        if (text.includes('Generate')) {
            e.preventDefault();
            window.location.href = '/create.html';
            return;
        }
    }

    // "+ Add New" buttons
    if (target.classList.contains('btn-primary')) {
        const text = target.textContent || '';
        if (text.includes('Character') || text.includes('World') || text.includes('Scene')) {
            e.preventDefault();
            window.location.href = '/create.html';
            return;
        }
    }
});
