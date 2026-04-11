interface StatusBarProps {
  message: string | null;
  isError?: boolean;
  onClose: () => void;
}

export function StatusBar({ message, isError = false, onClose }: StatusBarProps) {
  if (message === null) return null;

  return (
    <div
      className="status-bar"
      style={{ background: isError ? '#f8d7da' : '#e9ecef' }}
    >
      <span style={{ color: isError ? '#721c24' : '#333' }}>{message}</span>
      <button className="close-status-btn" onClick={onClose}>×</button>
    </div>
  );
}
