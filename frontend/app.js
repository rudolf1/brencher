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
const stateSelector = document.getElementById('state-selector');
const refreshBranchesBtn = document.getElementById('refresh-branches');
const applyChangesBtn = document.getElementById('apply-changes');
const branchFilter = document.getElementById('branch-filter');

let branches = [];
let filteredBranches = []; // Filtered list for display
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

function filterBranches() {
    const filterText = branchFilter.value.toLowerCase().trim();
    
    if (!filterText) {
        // Show branches that are either selected for deploy or currently deployed
        filteredBranches = branches.filter(({ env, branch }) => {
            const isSelected = selectedBranches.some(([branchName]) => branchName === branch);
            const isDeployed = deployedCommits[branch] && deployedCommits[branch] !== 'N/A';
            return isSelected || isDeployed || branches.length <= 10; // Show all if small list
        });
    } else {
        // Filter based on branch name, commit ID, or commit message
        filteredBranches = branches.filter(({ env, branch, commits }) => {
            // Check branch name
            if (branch.toLowerCase().includes(filterText)) return true;

            // Check deployed commit short hash
            const deployedCommit = deployedCommits[branch];
            if (deployedCommit && deployedCommit.toLowerCase().includes(filterText)) return true;

            // Check commits list
            if (Array.isArray(commits)) {
                return commits.some(c => {
                    const shortHash = c.hexsha ? c.hexsha.substring(0,8).toLowerCase() : '';
                    return (c.hexsha && c.hexsha.toLowerCase().includes(filterText)) ||
                           shortHash.includes(filterText) ||
                           (c.message && c.message.toLowerCase().includes(filterText)) ||
                           (c.author && c.author.toLowerCase().includes(filterText));
                });
            }
            return false;
        });
    }
    
    renderBranches();
}

function getCommitDropdownOptions(env, branchName, desiredCommit) {
    const branchObj = branches.find(b => b.env === env && b.branch === branchName);
    let options = '';
    const commits = branchObj && Array.isArray(branchObj.commits) ? branchObj.commits : [];

    if (commits.length) {
        const head = commits[0];
        const headShort = head.hexsha ? head.hexsha.substring(0,8) : '';
        options += `<option value="HEAD" ${desiredCommit === 'HEAD' ? 'selected' : ''}>HEAD (${headShort} - ${(head.author||'').substring(0,25)} - ${head.message ? head.message.substring(0,50) + (head.message.length>50?'...':'') : ''})</option>`;
        commits.forEach(c => {
            const full = c.hexsha;
            const shortHash = full ? full.substring(0,8) : '';
            const isSelected = desiredCommit === full || desiredCommit === shortHash;
            options += `<option value="${full}" ${isSelected ? 'selected' : ''}>${shortHash} - ${(c.author||'').substring(0,25)} - ${c.message ? c.message.substring(0,50)+(c.message.length>50?'...':'') : ''}</option>`;
        });
    } else {
        options += `<option value="HEAD" ${desiredCommit === 'HEAD' ? 'selected' : ''}>HEAD (no commits)</option>`;
    }

    const hasMatch = commits.some(c => {
        const full = c.hexsha;
        const shortHash = full ? full.substring(0,8) : '';
        return desiredCommit === full || desiredCommit === shortHash || desiredCommit === 'HEAD';
    });
    const isCustom = desiredCommit && desiredCommit !== 'HEAD' && !hasMatch;
    options += `<option value="custom" ${isCustom ? 'selected' : ''}>Custom Commit</option>`;
    return options;
}

function branchHasCommit(env, branchName, commit) {
    if (commit === 'HEAD') return true;
    const branchObj = branches.find(b => b.env === env && b.branch === branchName);
    if (!branchObj) return false;
    return branchObj.commits?.some(c => {
        const full = c.hexsha;
        const shortHash = full ? full.substring(0,8) : '';
        return commit === full || commit === shortHash;
    }) || false;
}

function renderBranches() {
    const branchesToShow = filteredBranches.length > 0 || branchFilter.value.trim() ? filteredBranches : branches;
    
    if (!branchesToShow.length) {
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
                ${branchesToShow.map(({ env, branch }) => {
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
                                <select class="desired-commit" data-branch="${branch}" data-env="${env}">
                                    ${getCommitDropdownOptions(env, branch, desiredCommit)}
                                </select>
                                <input type="text" class="commit-input" data-branch="${branch}" 
                                       value="${desiredCommit !== 'HEAD' && !branchHasCommit(env, branch, desiredCommit) ? desiredCommit : ''}" 
                                       placeholder="Enter commit ID"
                                       style="display: ${desiredCommit !== 'HEAD' && !branchHasCommit(env, branch, desiredCommit) ? 'inline-block' : 'none'};">
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
            const env = e.target.dataset.env;
            const commitInput = branchesList.querySelector(`.commit-input[data-branch="${branch}"]`);
            
            if (e.target.value === 'custom') {
                commitInput.style.display = 'inline-block';
                commitInput.focus();
            } else if (e.target.value === 'HEAD') {
                commitInput.style.display = 'none';
                updateBranchCommit(branch, 'HEAD');
            } else {
                // Selected a specific commit
                commitInput.style.display = 'none';
                updateBranchCommit(branch, e.target.value);
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

// Filter event handler
branchFilter.oninput = () => {
    filterBranches();
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
        // Expecting data: { env: { branchName: [ {full_hash, hash, author, message}, ... up to 10 ] } }
        branches = Object.entries(data).flatMap(([env, branchList]) => 
            Object.entries(branchList).map(([branchName, commitList]) => ({
                env: env,
                branch: branchName,
                commits: commitList
            }))
        );
        filterBranches(); // Use filter instead of direct render
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
        filterBranches(); // Use filter instead of direct render
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

function updateEnvironment() {
    const envUpdate = {
        id: environment && environment.length > 0 ? environment[0][0].id : null,
        branches: selectedBranches, // Send as [branch_name, desired_commit] pairs
        state: defaultState
    };
    wsEnv.emit('update', envUpdate);
}

// Initial load
setupSocketIO();
showStatus('Loading branches...');
renderBranches();
renderJobs();
