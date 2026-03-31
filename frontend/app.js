// Placeholder for frontend JS logic
// You can add your Socket.IO and UI code here
console.log('app.js loaded');

// WebSocket namespaces
const WS_BRANCHES = '/ws/branches';
const WS_ENVIRONMENT = '/ws/environment';
const WS_ERRORS = '/ws/errors';

// DOM refs
const branchesList = document.getElementById('branches-list');
const statusBar = document.getElementById('status-bar');
const statusMessage = document.getElementById('status-message');
const closeStatus = document.getElementById('close-status');
const refreshBranchesBtn = document.getElementById('refresh-branches');
const applyChangesBtn = document.getElementById('apply-changes');
const branchFilter = document.getElementById('branch-filter');

// Branches list (flattened) for UI rendering: [{ envId, envName, branch, commits: [] }]
let branches = [];
let filteredBranches = [];

// Toggle state: show all branches or filtered
let showAllBranches = false;

// Environment runtime state storage:
// environmentsRaw: array as received from backend: [ [envObj, jobsArr], ... ]
let environmentsRaw = [];

// Per-environment maps
// selectedBranchesByEnv: envId -> Array<[branch, desiredCommit]>
const selectedBranchesByEnv = {};
// serverSelectedBranchesByEnv mirrors server's last known selection for diffing
const serverSelectedBranchesByEnv = {};
// columnsByEnv: envId -> { columnName: { branchName: value } }
// Populated from any step result that contains a `columns` key (e.g. GitUnmerge)
const columnsByEnv = {};

// Socket instances
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
    // Determine if any environment has changed selections
    const changed = Object.keys(selectedBranchesByEnv).some(envId => {
        const localSel = [...(selectedBranchesByEnv[envId] || [])].sort();
        const serverSel = [...(serverSelectedBranchesByEnv[envId] || [])].sort();
        return JSON.stringify(localSel) !== JSON.stringify(serverSel);
    });
    if (changed) applyChangesBtn.classList.remove('hidden');
    else applyChangesBtn.classList.add('hidden');
}

function filterBranches() {
    const filterText = branchFilter.value.toLowerCase().trim();
    filteredBranches = branches.filter(({envId, branch, commits}) => {
        const selList = selectedBranchesByEnv[envId] || [];
        const isSelected = selList.some(([b]) => b === branch);
        // Always show branches that appear in any column (e.g. deployed branches from GitUnmerge)
        const envCols = columnsByEnv[envId] || {};
        const isInColumns = Object.values(envCols).some(colData => branch in colData);
        const isFiltered = !!filterText && branch.toLowerCase().includes(filterText);
        const isFilteredByCommit = !!filterText && Array.isArray(commits) && commits.some(c => {
            const shortHash = c.hexsha ? c.hexsha.substring(0, 8).toLowerCase() : '';
            return (c.hexsha && c.hexsha.toLowerCase().includes(filterText)) ||
                shortHash.includes(filterText) ||
                (c.message && c.message.toLowerCase().includes(filterText)) ||
                (c.author && c.author.toLowerCase().includes(filterText));
        });
        return showAllBranches || isSelected || isInColumns || isFiltered || isFilteredByCommit;
    });
    renderBranches();
}

function getCommitDropdownOptions(envId, branchName, desiredCommit) {
    const branchObj = branches.find(b => b.envId === envId && b.branch === branchName);
    let options = '';
    const commits = branchObj && Array.isArray(branchObj.commits) ? branchObj.commits : [];

    if (commits.length) {
        const head = commits[0];
        const headShort = head.hexsha ? head.hexsha.substring(0, 8) : '';
        options += `<option value="HEAD" ${desiredCommit === 'HEAD' ? 'selected' : ''}>HEAD (${headShort} - ${(head.author || '').substring(0, 25)} - ${head.message ? head.message.substring(0, 50) + (head.message.length > 50 ? '...' : '') : ''})</option>`;
        commits.forEach(c => {
            const full = c.hexsha;
            const shortHash = full ? full.substring(0, 8) : '';
            const isSelected = desiredCommit === full || desiredCommit === shortHash;
            options += `<option value="${full}" ${isSelected ? 'selected' : ''}>${shortHash} - ${(c.author || '').substring(0, 25)} - ${c.message ? c.message.substring(0, 50) + (c.message.length > 50 ? '...' : '') : ''}</option>`;
        });
    } else {
        options += `<option value="HEAD" ${desiredCommit === 'HEAD' ? 'selected' : ''}>HEAD (no commits)</option>`;
    }

    const hasMatch = commits.some(c => {
        const full = c.hexsha;
        const shortHash = full ? full.substring(0, 8) : '';
        return desiredCommit === full || desiredCommit === shortHash || desiredCommit === 'HEAD';
    });
    const isCustom = desiredCommit && desiredCommit !== 'HEAD' && !hasMatch;
    options += `<option value="custom" ${isCustom ? 'selected' : ''}>Custom Commit</option>`;
    return options;
}

function branchHasCommit(envId, branchName, commit) {
    if (commit === 'HEAD') return true;
    const branchObj = branches.find(b => b.envId === envId && b.branch === branchName);
    if (!branchObj) return false;
    return branchObj.commits?.some(c => {
        const full = c.hexsha;
        const shortHash = full ? full.substring(0, 8) : '';
        return commit === full || commit === shortHash;
    }) || false;
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

let renderedBranches = []

function renderBranches() {
    if (JSON.stringify(filteredBranches) === JSON.stringify(renderedBranches)) {
        return
    }
    checkForPendingChanges();

    const branchesToShow = filteredBranches.length > 0 || branchFilter.value.trim() ? filteredBranches : branches;
    if (!branchesToShow.length) {
        branchesList.innerHTML = '<p class="loading">No branches found.</p>';
        return;
    }

    // Group by envId for clearer separation
    const groups = branchesToShow.reduce((acc, b) => {
        acc[b.envId] = acc[b.envId] || {envName: b.envName, rows: []};
        acc[b.envId].rows.push(b);
        return acc;
    }, {});

    branchesList.innerHTML = Object.entries(groups).map(([envId, {envName, rows}]) => {
        const envCols = columnsByEnv[envId] || {};
        const colNames = Object.keys(envCols);
        return `
        <div class="env-block">
            <h3 class="env-title">Environment: ${envName || envId}</h3>
            <table class="branches-table">
                <thead>
                    <tr>
                        <th>Deploy</th>
                        <th>Branch</th>
                        <th>Desired Commit</th>
                        ${colNames.map(n => `<th>${escapeHtml(n)}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(({envId: eId, branch}) => {
            const selList = selectedBranchesByEnv[eId] || [];
            const pair = selList.find(([b]) => b === branch);
            const desiredCommit = pair ? pair[1] : 'HEAD';
            const hasCommit = branchHasCommit(eId, branch, desiredCommit);
            return `
                        <tr class="branch-row" data-env="${eId}" data-branch="${branch}">
                            <td><input type="checkbox" value="${branch}" data-env="${eId}" ${pair ? 'checked' : ''}></td>
                            <td>${branch}</td>
                            <td>
                                <select class="desired-commit" data-branch="${branch}" data-env="${eId}">
                                    ${getCommitDropdownOptions(eId, branch, desiredCommit)}
                                </select>
                                <input type="text" class="commit-input" data-branch="${branch}" data-env="${eId}"
                                       value="${desiredCommit !== 'HEAD' && !hasCommit ? desiredCommit : ''}"
                                       placeholder="Enter commit ID" style="display: ${desiredCommit !== 'HEAD' && !hasCommit ? 'inline-block' : 'none'};" />
                            </td>
                            ${colNames.map(n => `<td>${escapeHtml((envCols[n] && envCols[n][branch]) || '')}</td>`).join('')}
                        </tr>`;
        }).join('')}
                </tbody>
            </table>
        </div>`;
    }).join('');
    // Event wiring
    branchesList.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.onchange = e => {
            const branch = e.target.value;
            const envId = e.target.dataset.env;
            selectedBranchesByEnv[envId] = selectedBranchesByEnv[envId] || [];
            if (e.target.checked) {
                if (!selectedBranchesByEnv[envId].some(([b]) => b === branch)) {
                    selectedBranchesByEnv[envId].push([branch, 'HEAD']);
                }
            } else {
                selectedBranchesByEnv[envId] = selectedBranchesByEnv[envId].filter(([b]) => b !== branch);
            }
            checkForPendingChanges();
        };
    });
    branchesList.querySelectorAll('.desired-commit').forEach(sel => {
        sel.onchange = e => {
            const branch = e.target.dataset.branch;
            const envId = e.target.dataset.env;
            const commitInput = branchesList.querySelector(`.commit-input[data-env="${envId}"][data-branch="${branch}"]`);
            if (e.target.value === 'custom') {
                commitInput.style.display = 'inline-block';
                commitInput.focus();
            } else if (e.target.value === 'HEAD') {
                commitInput.style.display = 'none';
                updateBranchCommit(envId, branch, 'HEAD');
            } else {
                commitInput.style.display = 'none';
                updateBranchCommit(envId, branch, e.target.value);
            }
        };
    });
    branchesList.querySelectorAll('.commit-input').forEach(input => {
        input.onchange = input.onblur = e => {
            const branch = e.target.dataset.branch;
            const envId = e.target.dataset.env;
            const commitId = e.target.value.trim();
            updateBranchCommit(envId, branch, commitId || 'HEAD');
        };
    });
    renderedBranches = filteredBranches;
}

function updateBranchCommit(envId, branch, commit) {
    selectedBranchesByEnv[envId] = selectedBranchesByEnv[envId] || [];
    const idx = selectedBranchesByEnv[envId].findIndex(([b]) => b === branch);
    if (idx !== -1) selectedBranchesByEnv[envId][idx] = [branch, commit];
    checkForPendingChanges();
}

function renderJobs() {
    const jobsList = document.getElementById('jobs-list');
    if (!jobsList) return;
    if (!Array.isArray(environmentsRaw) || environmentsRaw.length === 0) {
        jobsList.innerHTML = '<p class="loading">No jobs found.</p>';
        return;
    }
    jobsList.innerHTML = environmentsRaw.map((envObj) => {
        var linksHtml = ""
        const jobsArr = envObj.pipeline || [];
        if (Array.isArray(jobsArr)) {
            linksHtml = jobsArr.flatMap(job => {
                const userLinks = [];
                const extractUserLinks = (obj) => {
                    if (!obj || typeof obj !== 'object') return;
                    if (obj.userLinks && typeof obj.userLinks === 'object') {
                        userLinks.push(...Object.entries(obj.userLinks));
                    }
                    for (const key in obj) {
                        if (typeof obj[key] === 'object') {
                            extractUserLinks(obj[key]);
                        }
                    }
                };
                extractUserLinks(job.status);
                return userLinks.map(([title, url]) =>
                    `<a href="${url}" target="_blank" rel="noopener noreferrer">${title}</a>`
                )
            })
                .join(' | ');
        }

        return `
            <div class="env-jobs">
            <h4>Environment: ${envObj.name || envObj.id || ''}</h4> 
            ${linksHtml ? `<div style="float:right">${linksHtml}</div>` : ''}
            ${Array.isArray(jobsArr) && jobsArr.length > 0
            ? jobsArr.map(job => {
                let statusDisplay = `<pre>` + JSON.stringify(job.status, null, 2) + `</pre>`;
                statusDisplay = statusDisplay.replace(
                    /(https?:\/\/[^\s"']+)/g,
                    url => `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`
                );
                const key = `${envObj.id}::${job.name}`;
                const storageKey = 'jobSpoiler:' + key;
                const safeId = 'spoiler-' + encodeURIComponent(key).replace(/[^a-zA-Z0-9_-]/g, '_');
                const isError = job.error;
                const openByDefault = isError || (window._jobSpoilerState && window._jobSpoilerState[storageKey] === 'open');

                return `
                    <div class="job-item">
                        <div class="job-header" style="cursor:pointer;font-weight:bold;"
                             onclick="toggleJobSpoiler('${key}', '${safeId}')">
                            ${isError
                    ? `<span style="color:#dc3545;font-weight:bold;margin-right:6px;" title="Error">!</span>`
                    : `<span style="color:#28a745;font-weight:bold;margin-right:6px;" title="OK">✔</span>`}
                            ${envObj.id} - ${job.name}
                        </div>
                        <div id="${safeId}" class="job-spoiler" style="display: ${openByDefault ? 'block' : 'none'}; margin-top:8px;">
                            ${statusDisplay}
                        </div>
                    </div>`;
            }).join('')
            : '<div class="job-item">No jobs found.</div>'}
            </div>`;
    }).join('');
}

toggleJobSpoiler = function (key, safeId) {
    try {
        const el = document.getElementById(safeId);
        if (!el) return;
        const storageKey = 'jobSpoiler:' + key;
        const isHidden = window.getComputedStyle(el).display === 'none';
        window._jobSpoilerState = window._jobSpoilerState || {};
        if (isHidden) {
            el.style.display = 'block';
            window._jobSpoilerState[storageKey] = 'open';
        } else {
            el.style.display = 'none';
            window._jobSpoilerState[storageKey] = 'closed';
        }
    } catch (err) {
        console.error('toggleJobSpoiler error', err);
    }
};
refreshBranchesBtn.onclick = () => {
    wsEnv.emit('update', {id: ""});
    showStatus('Refreshing...');
};

// Filter event handler
branchFilter.oninput = () => {
    filterBranches();
};

// Toggle show all button handler
const toggleShowAllBtn = document.getElementById('toggle-show-all');
if (toggleShowAllBtn) {
    toggleShowAllBtn.onclick = () => {
        showAllBranches = !showAllBranches;
        toggleShowAllBtn.textContent = showAllBranches ? 'Show Filtered' : 'Show All';
        filterBranches();
    };
}

// Apply changes button handler
applyChangesBtn.onclick = () => {
    updateEnvironment();
};

// Socket.IO setup
function setupSocketIO() {
    wsBranches = io(WS_BRANCHES);
    wsEnv = io(WS_ENVIRONMENT);
    wsErr = io(WS_ERRORS);

    wsBranches.on('branches', data => {
        // data: { envId: { branchName: commits[] } }
        branches = Object.entries(data).flatMap(([envId, branchMap]) =>
            Object.entries(branchMap).map(([branchName, commitList]) => {
                const envObj = (environmentsRaw.find((e) => e.id === envId) || [null])[0];
                return {
                    envId,
                    envName: envObj ? (envObj.name || envObj.id) : envId,
                    branch: branchName,
                    commits: commitList
                };
            })
        );
        filterBranches();
        showStatus('Branches updated.');
    });

    wsEnv.on('environments', data => {
        payload = data || {};
        environmentsRaw = Object.values(payload);

        // Sync selections and deployed commits per environment
        environmentsRaw.forEach((envObj) => {
            if (!envObj) return;
            const envId = envObj.id || envObj.name || 'unknown';
            // Branch selections
            if (Array.isArray(envObj.branches) && envObj.branches.length > 0) {
                if (Array.isArray(envObj.branches[0])) {
                    selectedBranchesByEnv[envId] = [...envObj.branches];
                } else {
                    selectedBranchesByEnv[envId] = envObj.branches.map(b => [b, 'HEAD']);
                }
                serverSelectedBranchesByEnv[envId] = [...selectedBranchesByEnv[envId]];
            } else if (!selectedBranchesByEnv[envId]) {
                selectedBranchesByEnv[envId] = [];
                serverSelectedBranchesByEnv[envId] = [];
            }
            // Extract columns from all job statuses
            columnsByEnv[envId] = {};
            const jobsArr = envObj.pipeline || [];
            if (Array.isArray(jobsArr)) {
                jobsArr.forEach(job => {
                    if (job.status == null || job.error) return;
                    const status = job.status;
                    // New structured format: status is an object with a `columns` key
                    if (typeof status === 'object' && !Array.isArray(status) && status.columns &&
                            typeof status.columns === 'object') {
                        Object.entries(status.columns).forEach(([colName, colData]) => {
                            if (colData && typeof colData === 'object' && !Array.isArray(colData)) {
                                columnsByEnv[envId][colName] = {...colData};
                            }
                        });
                    }
                    // Legacy list format from GitUnmerge: array of [branch_name, commit_hash]
                    if (job.name === 'GitUnmerge' && Array.isArray(status)) {
                        const deployedCol = {};
                        status.forEach(([branchName, commitHash]) => {
                            if (typeof branchName === 'string' && typeof commitHash === 'string') {
                                deployedCol[branchName] = commitHash.substring(0, 8);
                            }
                        });
                        if (Object.keys(deployedCol).length > 0) {
                            columnsByEnv[envId]['Deployed'] = deployedCol;
                        }
                    }
                });
            }
        });

        // Rebuild branches list environment names for rows already present
        branches = branches.map(b => {
            const envEntry = environmentsRaw.find((e) => (e.id || e.name) === b.envId);
            return {...b, envName: envEntry ? (envEntry.name || envEntry.id) : b.envName};
        });

        filterBranches();
        renderJobs();
        showStatus('Environments updated.');
    });

    wsEnv.on('disconnect', () => showStatus('Disconnected from environment websocket.', true));
    wsBranches.on('disconnect', () => showStatus('Disconnected from branches websocket.', true));
    wsErr.on('error', data => showStatus(data.message || 'Unknown error', true));
}

function updateEnvironment() {
    // Emit updates only for environments whose selection changed
    Object.keys(selectedBranchesByEnv).forEach(envId => {
        const localSel = [...(selectedBranchesByEnv[envId] || [])].sort();
        const serverSel = [...(serverSelectedBranchesByEnv[envId] || [])].sort();
        if (JSON.stringify(localSel) !== JSON.stringify(serverSel)) {
            wsEnv.emit('update', {id: envId, branches: selectedBranchesByEnv[envId]});
            // Optimistically sync server state
            serverSelectedBranchesByEnv[envId] = [...selectedBranchesByEnv[envId]];
            branchFilter.value = '';
        }
    });
    checkForPendingChanges();
    showStatus('Changes applied (pending server confirmation).');
}

// Initial load
setupSocketIO();
showStatus('Loading branches...');
renderBranches();
renderJobs();
