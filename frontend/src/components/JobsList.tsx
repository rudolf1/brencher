import { useRef, useState } from 'react';
import type { EnvironmentDto, PipelineStep } from '../types/index';

interface JobsListProps {
  environments: EnvironmentDto[];
}

function extractUserLinks(obj: unknown): [string, string][] {
  if (!obj || typeof obj !== 'object') return [];
  const result: [string, string][] = [];
  const rec = obj as Record<string, unknown>;
  if (rec.userLinks && typeof rec.userLinks === 'object' && !Array.isArray(rec.userLinks)) {
    const links = rec.userLinks as Record<string, unknown>;
    for (const [title, url] of Object.entries(links)) {
      if (typeof url === 'string') result.push([title, url]);
    }
  }
  for (const key of Object.keys(rec)) {
    if (typeof rec[key] === 'object') {
      result.push(...extractUserLinks(rec[key]));
    }
  }
  return result;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function isValidHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

function linkifyText(text: string): string {
  const escaped = escapeHtml(text);
  return escaped.replace(
    /(https?:\/\/[^\s&"'<>]+)/g,
    (url) => {
      // Decode HTML entities that may have been escaped (e.g. &amp; → &)
      const rawUrl = url.replace(/&amp;/g, '&');
      if (!isValidHttpUrl(rawUrl)) return url;
      const safeHref = escapeHtml(rawUrl);
      return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${url}</a>`;
    }
  );
}

interface JobItemProps {
  envId: string;
  job: PipelineStep;
  defaultOpen: boolean;
}

function JobItem({ envId, job, defaultOpen }: JobItemProps) {
  const [open, setOpen] = useState(defaultOpen);
  const initialOpenRef = useRef(defaultOpen);

  // Keep error jobs open by default (tracked via ref so it doesn't reset on re-render)
  const isOpen = job.error ? (initialOpenRef.current ? true : open) : open;

  const statusJson = JSON.stringify(job.status, null, 2);
  const statusHtml = linkifyText(statusJson);

  return (
    <div className="job-item">
      <div
        className="job-header"
        style={{ cursor: 'pointer', fontWeight: 'bold' }}
        onClick={() => setOpen((o) => !o)}
      >
        {job.error ? (
          <span style={{ color: '#dc3545', fontWeight: 'bold', marginRight: 6 }} title="Error">!</span>
        ) : (
          <span style={{ color: '#28a745', fontWeight: 'bold', marginRight: 6 }} title="OK">✔</span>
        )}
        {envId} - {job.name}
      </div>
      {isOpen && (
        <div className="job-spoiler" style={{ marginTop: 8 }}>
          <pre dangerouslySetInnerHTML={{ __html: statusHtml }} />
        </div>
      )}
    </div>
  );
}

export function JobsList({ environments }: JobsListProps) {
  if (environments.length === 0) {
    return (
      <div className="jobs-list">
        <p className="loading">No jobs found.</p>
      </div>
    );
  }

  return (
    <div className="jobs-list">
      {environments.map((envObj) => {
        const jobsArr = envObj.pipeline ?? [];

        const allLinks: [string, string][] = jobsArr.flatMap((job) =>
          extractUserLinks(job.status)
        );

        return (
          <div key={envObj.id} className="env-jobs">
            <h4>Environment: {envObj.id}</h4>
            {allLinks.length > 0 && (
              <div style={{ float: 'right' }}>
                {allLinks.map(([title, url], i) => (
                  <span key={i}>
                    {i > 0 && ' | '}
                    <a href={url} target="_blank" rel="noopener noreferrer">{title}</a>
                  </span>
                ))}
              </div>
            )}
            {jobsArr.length > 0 ? (
              jobsArr.map((job, idx) => (
                <JobItem
                  key={`${envObj.id}::${job.name}::${idx}`}
                  envId={envObj.id}
                  job={job}
                  defaultOpen={job.error === true}
                />
              ))
            ) : (
              <div className="job-item">No jobs found.</div>
            )}
          </div>
        );
      })}
    </div>
  );
}
