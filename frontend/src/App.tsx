import { useCallback, useEffect, useMemo, useState } from 'react';
import './App.css';
import { BranchesList } from './components/BranchesList';
import type { BranchItem, ColumnsByEnv, SelectedBranches } from './components/BranchesList';
import { JobsList } from './components/JobsList';
import { StatusBar } from './components/StatusBar';
import { useWebSocket } from './hooks/useWebSocket';
import type { BranchCommitPair, EnvironmentDto } from './types/index';

export function App() {
  const { sendMessage, lastBranchesMessage, lastEnvironmentsMessage, lastError, connectionStatus } =
    useWebSocket();

  const [branches, setBranches] = useState<BranchItem[]>([]);
  const [environments, setEnvironments] = useState<EnvironmentDto[]>([]);
  const [selectedBranchesByEnv, setSelectedBranchesByEnv] = useState<SelectedBranches>({});
  const [serverSelectedBranchesByEnv, setServerSelectedBranchesByEnv] = useState<SelectedBranches>({});
  const [columnsByEnv, setColumnsByEnv] = useState<ColumnsByEnv>({});
  const [filterText, setFilterText] = useState('');
  const [showAll, setShowAll] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>('Loading branches...');
  const [isStatusError, setIsStatusError] = useState(false);

  const showStatus = useCallback((message: string, isError = false) => {
    setStatusMessage(message);
    setIsStatusError(isError);
  }, []);

  // Handle incoming branches
  useEffect(() => {
    if (!lastBranchesMessage) return;
    const data = lastBranchesMessage;
    setBranches(() => {
      const next: BranchItem[] = Object.entries(data).flatMap(([envId, branchMap]) =>
        Object.entries(branchMap).map(([branchName, commitList]) => ({
          envId,
          branch: branchName,
          commits: commitList,
        }))
      );
      // Replace all branches with the latest data from the server
      return next;
    });
    showStatus('Branches updated.');
  }, [lastBranchesMessage, showStatus]);

  // Handle incoming environments
  useEffect(() => {
    if (!lastEnvironmentsMessage) return;
    const payload = lastEnvironmentsMessage;
    const envList = Object.values(payload);
    setEnvironments(envList);

    setSelectedBranchesByEnv((prevSelected) => {
      // We need server state inline to check pending changes; use functional update
      let nextSelected = prevSelected;
      setServerSelectedBranchesByEnv((prevServer) => {
        // Check if changes are pending before overwriting selections
        const hasPending = Object.keys(prevSelected).some((envId) => {
          const localSel = [...(prevSelected[envId] ?? [])].sort((a, b) =>
            JSON.stringify(a).localeCompare(JSON.stringify(b))
          );
          const serverSel = [...(prevServer[envId] ?? [])].sort((a, b) =>
            JSON.stringify(a).localeCompare(JSON.stringify(b))
          );
          return JSON.stringify(localSel) !== JSON.stringify(serverSel);
        });

        const nextServerState = { ...prevServer };
        const updatedSelected = { ...prevSelected };

        envList.forEach((envObj) => {
          const envId = envObj.id;
          if (!hasPending) {
            if (Array.isArray(envObj.branches) && envObj.branches.length > 0) {
              const pairs: BranchCommitPair[] = Array.isArray(envObj.branches[0])
                ? (envObj.branches as BranchCommitPair[])
                : envObj.branches.map((b) => [b as unknown as string, 'HEAD'] as BranchCommitPair);
              updatedSelected[envId] = [...pairs];
              nextServerState[envId] = [...pairs];
            } else if (!updatedSelected[envId]) {
              updatedSelected[envId] = [];
              nextServerState[envId] = [];
            }
          }
        });

        nextSelected = updatedSelected;
        return nextServerState;
      });

      return nextSelected;
    });

    // Extract column data from pipeline steps
    setColumnsByEnv((prev) => {
      const next = { ...prev };
      envList.forEach((envObj) => {
        const envId = envObj.id;
        next[envId] = {};
        const jobsArr = envObj.pipeline ?? [];
        jobsArr.forEach((job) => {
          if (job.status == null || job.error) return;
          const status = job.status;
          if (
            typeof status === 'object' &&
            !Array.isArray(status) &&
            status !== null &&
            'columns' in status
          ) {
            const cols = (status as Record<string, unknown>).columns;
            if (cols && typeof cols === 'object' && !Array.isArray(cols)) {
              Object.entries(cols as Record<string, unknown>).forEach(([colName, colData]) => {
                if (colData && typeof colData === 'object' && !Array.isArray(colData)) {
                  next[envId][colName] = colData as Record<string, string>;
                }
              });
            }
          }
        });
      });
      return next;
    });

    showStatus('Environments updated.');
  }, [lastEnvironmentsMessage, showStatus]);

  // Handle incoming errors
  useEffect(() => {
    if (!lastError) return;
    showStatus(lastError.message || 'Unknown error', true);
  }, [lastError, showStatus]);

  // Show connection status changes
  useEffect(() => {
    if (connectionStatus === 'disconnected') {
      showStatus('Disconnected from server.', true);
    }
  }, [connectionStatus, showStatus]);

  const isChangesPending = useMemo(() => {
    return Object.keys(selectedBranchesByEnv).some((envId) => {
      const localSel = [...(selectedBranchesByEnv[envId] ?? [])].sort((a, b) =>
        JSON.stringify(a).localeCompare(JSON.stringify(b))
      );
      const serverSel = [...(serverSelectedBranchesByEnv[envId] ?? [])].sort((a, b) =>
        JSON.stringify(a).localeCompare(JSON.stringify(b))
      );
      return JSON.stringify(localSel) !== JSON.stringify(serverSel);
    });
  }, [selectedBranchesByEnv, serverSelectedBranchesByEnv]);

  const filteredBranches = useMemo(() => {
    const text = filterText.toLowerCase().trim();
    return branches.filter(({ envId, branch, commits }) => {
      const selList = selectedBranchesByEnv[envId] ?? [];
      const isSelected = selList.some(([b]) => b === branch);

      const envCols = columnsByEnv[envId] ?? {};
      const isInColumns = Object.values(envCols).some((colData) => branch in colData);

      if (showAll) return true;
      if (isSelected || isInColumns) return true;
      if (!text) return false;

      if (branch.toLowerCase().includes(text)) return true;
      return commits.some((c) => {
        const shortHash = c.hexsha ? c.hexsha.substring(0, 8).toLowerCase() : '';
        return (
          c.hexsha?.toLowerCase().includes(text) ||
          shortHash.includes(text) ||
          c.message?.toLowerCase().includes(text) ||
          c.author?.toLowerCase().includes(text)
        );
      });
    });
  }, [branches, filterText, showAll, selectedBranchesByEnv, columnsByEnv]);

  const handleSelectionChange = useCallback((envId: string, updated: BranchCommitPair[]) => {
    setSelectedBranchesByEnv((prev) => ({ ...prev, [envId]: updated }));
  }, []);

  const handleApplyChanges = useCallback(() => {
    Object.keys(selectedBranchesByEnv).forEach((envId) => {
      const localSel = [...(selectedBranchesByEnv[envId] ?? [])].sort((a, b) =>
        JSON.stringify(a).localeCompare(JSON.stringify(b))
      );
      const serverSel = [...(serverSelectedBranchesByEnv[envId] ?? [])].sort((a, b) =>
        JSON.stringify(a).localeCompare(JSON.stringify(b))
      );
      if (JSON.stringify(localSel) !== JSON.stringify(serverSel)) {
        sendMessage({ update: { id: envId, branches: selectedBranchesByEnv[envId] } });
        setServerSelectedBranchesByEnv((prev) => ({
          ...prev,
          [envId]: [...(selectedBranchesByEnv[envId] ?? [])],
        }));
      }
    });
    setFilterText('');
    showStatus('Changes applied (pending server confirmation).');
  }, [selectedBranchesByEnv, serverSelectedBranchesByEnv, sendMessage, showStatus]);

  const handleRefresh = useCallback(() => {
    sendMessage({ update: { id: '' } });
    showStatus('Refreshing...');
  }, [sendMessage, showStatus]);

  return (
    <div className="container">
      <header>
        <h1>Brencher - Branch Merger</h1>
        <StatusBar
          message={statusMessage}
          isError={isStatusError}
          onClose={() => setStatusMessage(null)}
        />
      </header>

      <main>
        <div className="branches-section">
          <div className="branches-header">
            <h2>Git Branches</h2>
            <div className="branches-controls-left">
              <input
                type="text"
                className="filter-input"
                placeholder="Filter branches by name, commit ID, or commit message..."
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
              />
              <button
                className="toggle-button"
                onClick={() => setShowAll((v) => !v)}
              >
                {showAll ? 'Show Filtered' : 'Show All'}
              </button>
            </div>
            <div className="branches-controls-right">
              {isChangesPending && (
                <button className="apply-button" onClick={handleApplyChanges}>
                  Apply Changes
                </button>
              )}
              <button className="refresh-button" onClick={handleRefresh}>
                Refresh Branches
              </button>
            </div>
          </div>

          <div className="branches-list">
            <BranchesList
              branches={filteredBranches}
              environments={environments}
              selectedBranchesByEnv={selectedBranchesByEnv}
              columnsByEnv={columnsByEnv}
              onSelectionChange={handleSelectionChange}
            />
          </div>
        </div>

        <div className="jobs-section">
          <h2>Jobs</h2>
          <JobsList environments={environments} />
        </div>
      </main>
    </div>
  );
}
