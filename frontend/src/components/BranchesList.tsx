import type { BranchCommitPair, CommitInfo, EnvironmentDto } from '../types/index';

export interface BranchItem {
  envId: string;
  branch: string;
  commits: CommitInfo[];
}

export type SelectedBranches = Record<string, BranchCommitPair[]>;
export type ColumnsByEnv = Record<string, Record<string, Record<string, string>>>;

interface BranchesListProps {
  branches: BranchItem[];
  environments: EnvironmentDto[];
  selectedBranchesByEnv: SelectedBranches;
  columnsByEnv: ColumnsByEnv;
  onSelectionChange: (envId: string, branches: BranchCommitPair[]) => void;
}

function getCommitOptions(commits: CommitInfo[], desiredCommit: string): { value: string; label: string; selected: boolean }[] {
  const opts: { value: string; label: string; selected: boolean }[] = [];

  if (commits.length > 0) {
    const head = commits[0];
    const headShort = head.hexsha ? head.hexsha.substring(0, 8) : '';
    const headAuthor = (head.author || '').substring(0, 25);
    const headMsg = head.message
      ? head.message.substring(0, 50) + (head.message.length > 50 ? '...' : '')
      : '';
    opts.push({
      value: 'HEAD',
      label: `HEAD (${headShort} - ${headAuthor} - ${headMsg})`,
      selected: desiredCommit === 'HEAD',
    });
    for (const c of commits) {
      const full = c.hexsha;
      const shortHash = full ? full.substring(0, 8) : '';
      const author = (c.author || '').substring(0, 25);
      const msg = c.message
        ? c.message.substring(0, 50) + (c.message.length > 50 ? '...' : '')
        : '';
      opts.push({
        value: full,
        label: `${shortHash} - ${author} - ${msg}`,
        selected: desiredCommit === full || desiredCommit === shortHash,
      });
    }
  } else {
    opts.push({ value: 'HEAD', label: 'HEAD (no commits)', selected: desiredCommit === 'HEAD' });
  }

  const hasMatch = commits.some(
    (c) => desiredCommit === c.hexsha || desiredCommit === c.hexsha?.substring(0, 8) || desiredCommit === 'HEAD'
  );
  const isCustom = desiredCommit && desiredCommit !== 'HEAD' && !hasMatch;
  opts.push({ value: 'custom', label: 'Custom Commit', selected: isCustom });
  return opts;
}

function branchHasCommit(commits: CommitInfo[], commit: string): boolean {
  if (commit === 'HEAD') return true;
  return commits.some((c) => c.hexsha === commit || c.hexsha?.substring(0, 8) === commit);
}

interface BranchRowProps {
  envId: string;
  branch: string;
  commits: CommitInfo[];
  selectedBranches: BranchCommitPair[];
  colNames: string[];
  colData: Record<string, Record<string, string>>;
  onSelectionChange: (branches: BranchCommitPair[]) => void;
}

function BranchRow({ envId, branch, commits, selectedBranches, colNames, colData, onSelectionChange }: BranchRowProps) {
  const pair = selectedBranches.find(([b]) => b === branch);
  const isChecked = !!pair;
  const desiredCommit = pair ? pair[1] : 'HEAD';
  const isCustom = desiredCommit !== 'HEAD' && !branchHasCommit(commits, desiredCommit);

  const updateCommit = (commit: string) => {
    const updated = selectedBranches.map(([b, c]) => (b === branch ? [b, commit] as BranchCommitPair : [b, c] as BranchCommitPair));
    onSelectionChange(updated);
  };

  const handleCheckbox = (checked: boolean) => {
    if (checked) {
      if (!selectedBranches.some(([b]) => b === branch)) {
        onSelectionChange([...selectedBranches, [branch, 'HEAD']]);
      }
    } else {
      onSelectionChange(selectedBranches.filter(([b]) => b !== branch));
    }
  };

  const handleDropdownChange = (value: string) => {
    if (value === 'custom') {
      // show text input - handled via isCustom state derived from desiredCommit
      updateCommit('');
    } else if (value === 'HEAD') {
      updateCommit('HEAD');
    } else {
      updateCommit(value);
    }
  };

  const dropdownValue = isCustom ? 'custom' : desiredCommit;
  const options = getCommitOptions(commits, desiredCommit);

  return (
    <tr className="branch-row" data-env={envId} data-branch={branch}>
      <td>
        <input
          type="checkbox"
          checked={isChecked}
          onChange={(e) => handleCheckbox(e.target.checked)}
        />
      </td>
      <td className="branch-name">{branch}</td>
      <td>
        <select
          className="desired-commit"
          value={dropdownValue}
          onChange={(e) => handleDropdownChange(e.target.value)}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        {isCustom && (
          <input
            type="text"
            className="commit-input"
            value={desiredCommit}
            placeholder="Enter commit ID"
            onChange={(e) => updateCommit(e.target.value)}
            onBlur={(e) => {
              const val = e.target.value.trim();
              updateCommit(val || 'HEAD');
            }}
          />
        )}
      </td>
      {colNames.map((colName) => (
        <td key={colName}>{colData[colName]?.[branch] ?? ''}</td>
      ))}
    </tr>
  );
}

export function BranchesList({
  branches,
  environments: _environments,
  selectedBranchesByEnv,
  columnsByEnv,
  onSelectionChange,
}: BranchesListProps) {
  if (branches.length === 0) {
    return <p className="loading">No branches found.</p>;
  }

  // Group branches by envId
  const groups = branches.reduce<Record<string, BranchItem[]>>((acc, b) => {
    acc[b.envId] = acc[b.envId] ?? [];
    acc[b.envId].push(b);
    return acc;
  }, {});

  return (
    <>
      {Object.entries(groups).map(([envId, rows]) => {
        const envCols = columnsByEnv[envId] ?? {};
        const colNames = Object.keys(envCols);
        const selectedBranches = selectedBranchesByEnv[envId] ?? [];

        return (
          <div key={envId} className="env-block">
            <h3 className="env-title">Environment: {envId}</h3>
            <table className="branches-table">
              <thead>
                <tr>
                  <th>Deploy</th>
                  <th>Branch</th>
                  <th>Desired Commit</th>
                  {colNames.map((n) => <th key={n}>{n}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.map(({ branch, commits }) => (
                  <BranchRow
                    key={`${envId}-${branch}`}
                    envId={envId}
                    branch={branch}
                    commits={commits}
                    selectedBranches={selectedBranches}
                    colNames={colNames}
                    colData={envCols}
                    onSelectionChange={(updated) => onSelectionChange(envId, updated)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </>
  );
}
