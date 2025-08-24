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
const applyChangesBtn = document.getElementById('apply-changes');

let branches = [];
let selectedBranches = []; // Array of [branch_name, desired_commit] pairs
let releases = [];
let defaultState = 'Active';
let environment = null;
let jobs = [];
let branchStates = {};
let deployedCommits = {}; // Stores current deployed commit info from GitUnmerge

// Server state tracking for change detection
let serverSelectedBranches = []; // Array of [branch_name, desired_commit] pairs
let serverDefaultState = 'Active';

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

function checkForPendingChanges() {
    // Check if selected branches differ (comparing [branch_name, commit] pairs)
    const selectedChanged = JSON.stringify([...selectedBranches].sort()) !== JSON.stringify([...serverSelectedBranches].sort());
    
    // Check if default state differs
    const defaultStateChanged = defaultState !== serverDefaultState;
    
    const hasChanges = selectedChanged || defaultStateChanged;
    
    if (hasChanges) {
        applyChangesBtn.classList.remove('hidden');
    } else {
        applyChangesBtn.classList.add('hidden');
    }
}

function renderBranches() {
    if (!branches.length) {
        branchesList.innerHTML = '<p class="loading">No branches found.</p>';
        return;
    }
    
    // Create table structure for branches
    branchesList.innerHTML = `
        <table class="branches-table">
            <thead>
                <tr>
                    <th>Deploy</th>
                    <th>Branch Name</th>
                    <th>Desired Commit</th>
                    <th>Current Deployed</th>
                </tr>
            </thead>
            <tbody>
                ${branches.map(({ env, branch }) => {
                    const isSelected = selectedBranches.some(([branchName]) => branchName === branch);
                    const selectedPair = selectedBranches.find(([branchName]) => branchName === branch);
                    const desiredCommit = selectedPair ? selectedPair[1] : 'HEAD';
                    const deployedCommit = deployedCommits[branch] || 'N/A';
                    
                    return `
                        <tr class="branch-row">
                            <td>
                                <input type="checkbox" value="${branch}" ${isSelected ? 'checked' : ''}>
                            </td>
                            <td class="branch-name">
                                ${branch} <span class="env-label">(${env})</span>
                            </td>
                            <td>
                                <select class="desired-commit" data-branch="${branch}">
                                    <option value="HEAD" ${desiredCommit === 'HEAD' ? 'selected' : ''}>HEAD</option>
                                    <option value="custom" ${desiredCommit !== 'HEAD' ? 'selected' : ''}>Custom Commit</option>
                                </select>
                                <input type="text" class="commit-input" data-branch="${branch}" 
                                       value="${desiredCommit !== 'HEAD' ? desiredCommit : ''}" 
                                       placeholder="Enter commit ID"
                                       style="display: ${desiredCommit !== 'HEAD' ? 'inline-block' : 'none'};">
                            </td>
                            <td class="deployed-commit">
                                ${deployedCommit}
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    // Attach event listeners
    branchesList.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.onchange = (e) => {
            const branch = e.target.value;
            if (e.target.checked) {
                if (!selectedBranches.some(([branchName]) => branchName === branch)) {
                    selectedBranches.push([branch, 'HEAD']);
                }
            } else {
                selectedBranches = selectedBranches.filter(([branchName]) => branchName !== branch);
            }
            checkForPendingChanges();
        };
    });
    
    branchesList.querySelectorAll('.desired-commit').forEach(sel => {
        sel.onchange = (e) => {
            const branch = e.target.dataset.branch;
            const commitInput = branchesList.querySelector(`.commit-input[data-branch="${branch}"]`);
            
            if (e.target.value === 'custom') {
                commitInput.style.display = 'inline-block';
                commitInput.focus();
            } else {
                commitInput.style.display = 'none';
                updateBranchCommit(branch, 'HEAD');
            }
        };
    });
    
    branchesList.querySelectorAll('.commit-input').forEach(input => {
        input.onchange = input.onblur = (e) => {
            const branch = e.target.dataset.branch;
            const commitId = e.target.value.trim();
            updateBranchCommit(branch, commitId || 'HEAD');
        };
    });
}

function updateBranchCommit(branch, commit) {
    const index = selectedBranches.findIndex(([branchName]) => branchName === branch);
    if (index !== -1) {
        selectedBranches[index] = [branch, commit];
        checkForPendingChanges();
    }
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
            <strong>${job.name}</strong> - ${JSON.stringify(job.status)}
        </div>`
    }).join('');
}

stateSelector.onchange = (e) => {
    defaultState = e.target.value;
    checkForPendingChanges(); // Check for changes instead of immediate update
};

refreshBranchesBtn.onclick = () => {
    fetchBranches();
    showStatus('Refreshing branches...');
};

// Apply changes button handler
applyChangesBtn.onclick = () => {
    updateEnvironment();
    // Update server state tracking to match current state
    serverSelectedBranches = [...selectedBranches];
    serverDefaultState = defaultState;
    checkForPendingChanges(); // This will hide the Apply button
    showStatus('Changes applied successfully.');
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
        // Sync selectedBranches with EnvironmentDto
        if (Array.isArray(environment) && environment.length > 0 && environment[0][0] && environment[0][0].branches) {
            // Convert branches to [branch_name, desired_commit] pairs
            if (Array.isArray(environment[0][0].branches) && environment[0][0].branches.length > 0) {
                if (Array.isArray(environment[0][0].branches[0])) {
                    // Already in [branch_name, desired_commit] format
                    selectedBranches = [...environment[0][0].branches];
                } else {
                    // Convert from simple branch names to [branch_name, 'HEAD'] pairs
                    selectedBranches = environment[0][0].branches.map(b => [b, 'HEAD']);
                }
            }
            // Update server state tracking
            serverSelectedBranches = [...selectedBranches];
        }
        
        // Extract deployed commits from GitUnmerge results if available
        if (Array.isArray(environment) && environment.length > 0 && environment[0][1]) {
            const gitUnmergeResults = environment[0][1].find(job => job.name === 'GitUnmerge');
            if (gitUnmergeResults && gitUnmergeResults.status && Array.isArray(gitUnmergeResults.status)) {
                deployedCommits = {};
                gitUnmergeResults.status.forEach(([commitHash, branchNames]) => {
                    if (Array.isArray(branchNames)) {
                        branchNames.forEach(branchName => {
                            deployedCommits[branchName] = commitHash.substring(0, 8); // Show short hash
                        });
                    }
                });
            }
        }
        
        // Update server state tracking for default state
        serverDefaultState = defaultState;
        renderBranches();
        renderJobs();
        checkForPendingChanges(); // Check if Apply button should be shown
        showStatus('Environment updated via Socket.IO.');
    });

    wsEnv.on('disconnect', () => {
        showStatus('Disconnected from environment websocket.', true);
    });
    wsBranches.on('disconnect', () => {
        showStatus('Disconnected from branches websocket.', true);
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
        id: environment && environment.length > 0 ? environment[0][0].id : null,
        branches: selectedBranches, // Send as [branch_name, desired_commit] pairs
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
