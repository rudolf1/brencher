// Placeholder for frontend JS logic
// You can add your Socket.IO and UI code here
console.log('app.js loaded');

const socket = io();

const WS_BRANCHES = '/ws/branches';
const WS_ENVIRONMENT = '/ws/environment';
const WS_ERRORS = '/ws/errors';

const branchesList = document.getElementById('branches-list');
const releasesList = document.getElementById('releases-list');
const statusBar = document.getElementById('status-bar');
const statusMessage = document.getElementById('status-message');
const closeStatus = document.getElementById('close-status');
const createReleaseBtn = document.getElementById('create-release');
const stateSelector = document.getElementById('state-selector');
const refreshBranchesBtn = document.getElementById('refresh-branches');

let branches = [];
let selectedBranches = [];
let releases = [];
let defaultState = 'Active';
let environment = null;
let jobs = [];
let branchStates = {};

let wsBranches = null;
let wsEnv = null;
let wsErr = null;

function showStatus(message, isError = false) {
    statusMessage.textContent = message;
    statusBar.classList.remove('hidden');
    statusBar.style.background = isError ? '#f8d7da' : '#e9ecef';
    statusMessage.style.color = isError ? '#721c24' : '#333';
}
closeStatus.onclick = () => statusBar.classList.add('hidden');

function renderBranches() {
    if (!branches.length) {
        branchesList.innerHTML = '<p class="loading">No branches found.</p>';
        return;
    }
    branchesList.innerHTML = branches.map(({ env, branch }) => `
        <div class="branch-item">
            <label>
                <input type="checkbox" value="${branch}" ${selectedBranches.includes(branch) ? 'checked' : ''}>
                ${branch} <span class="env-label">(${env})</span>
            </label>
            <select class="branch-state" data-branch="${branch}">
                <option value="Active" ${branchStates[branch]==='Active'?'selected':''}>Active</option>
                <option value="Pause" ${branchStates[branch]==='Pause'?'selected':''}>Pause</option>
            </select>
        </div>
    `).join('');
    branchesList.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.onchange = (e) => {
            const value = e.target.value;
            if (e.target.checked) {
                if (!selectedBranches.includes(value)) selectedBranches.push(value);
            } else {
                selectedBranches = selectedBranches.filter(b => b !== value);
            }
        };
    });
    branchesList.querySelectorAll('.branch-state').forEach(sel => {
        sel.onchange = (e) => {
            branchStates[e.target.dataset.branch] = e.target.value;
        };
    });
}

function renderReleases() {
    if (!releases.length) {
        releasesList.innerHTML = '<p class="loading">No releases found.</p>';
        return;
    }
    releasesList.innerHTML = releases.map(r => `
        <div class="release-item">
            <strong>ID:</strong> ${r.id}<br>
            <strong>Branches:</strong> ${r.branches.join(', ')}<br>
            <strong>State:</strong> ${r.state}<br>
            <strong>Git URL:</strong> ${r.git_url}<br>
        </div>
    `).join('');
}

function renderJobs() {
    const jobsList = document.getElementById('jobs-list');
    if (!jobsList) return;
    if (!environment) return;
    if (!environment.length) {
        jobsList.innerHTML = '<p class="loading">No jobs found.</p>';
        return;
    }

    jobsList.innerHTML = environment[0][1].map(job => {
        return `<div class="job-item">
            <strong>${job.name}</strong> - ${job.status}
        </div>`
    }).join('');
}

stateSelector.onchange = (e) => {
    defaultState = e.target.value;
};

refreshBranchesBtn.onclick = () => {
    fetchBranches();
    showStatus('Refreshing branches...');
};

// Socket.IO setup
function setupSocketIO() {
    wsBranches = io(WS_BRANCHES);
    wsEnv = io(WS_ENVIRONMENT);
    wsErr = io(WS_ERRORS);

    wsBranches.on('branches', (data) => {
        branches = Object.entries(data).flatMap(([env, branchList]) => branchList.map(branch => ({ env, branch })));
        renderBranches();
        showStatus('Branches updated via Socket.IO.');
    });

    wsEnv.on('environments', (data) => {
        environment = data;
        renderBranches();
        renderJobs()
        showStatus('Environment updated via Socket.IO.');
    });

    wsErr.on('error', (data) => {
        showStatus(data.message || 'Unknown error', true);
    });
}

function sendEnvironmentUpdate(envUpdate) {
    wsEnv.emit('update', envUpdate);
}

function updateEnvironment() {
    const envUpdate = {
        branches: selectedBranches.map(branch => [branch, branch]), // adjust as needed
        state: defaultState
    };
    sendEnvironmentUpdate(envUpdate);
}

// Initial load
setupSocketIO();
showStatus('Loading branches...');
renderBranches();
renderReleases();
renderJobs();
