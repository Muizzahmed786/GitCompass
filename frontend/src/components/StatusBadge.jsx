/**
 * StatusBadge — A reusable health/status indicator.
 *
 * Displays a colored dot + label that reflects the current state
 * of a service or resource (backend API status, repository mining status).
 */

const STATUS_STYLES = {
  // API health statuses
  ok: {
    dot: "bg-success",
    bg: "bg-success-light",
    text: "text-success",
    label: "Connected",
  },
  degraded: {
    dot: "bg-warning",
    bg: "bg-warning-light",
    text: "text-warning",
    label: "Degraded",
  },
  error: {
    dot: "bg-error",
    bg: "bg-error-light",
    text: "text-error",
    label: "Error",
  },
  loading: {
    dot: "bg-text-tertiary",
    bg: "bg-surface-hover",
    text: "text-text-secondary",
    label: "Checking…",
  },

  // Repository mining statuses
  pending: {
    dot: "bg-primary-400",
    bg: "bg-primary-50",
    text: "text-primary-700",
    label: "Pending",
    pulse: true,
  },
  cloning: {
    dot: "bg-primary-500",
    bg: "bg-primary-50",
    text: "text-primary-700",
    label: "Cloning…",
    pulse: true,
  },
  mining: {
    dot: "bg-primary-600",
    bg: "bg-primary-100",
    text: "text-primary-700",
    label: "Mining Git log…",
    pulse: true,
  },
  ready: {
    dot: "bg-success",
    bg: "bg-success-light",
    text: "text-success",
    label: "Ready",
  },
};

export default function StatusBadge({ status = "loading", label }) {
  const style = STATUS_STYLES[status] || {
    dot: "bg-text-tertiary",
    bg: "bg-surface-hover",
    text: "text-text-secondary",
    label: status,
  };
  const displayLabel = label || style.label;

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 
        px-2.5 py-1 rounded-full text-xs font-medium
        ${style.bg} ${style.text}
        transition-all duration-200
      `}
    >
      <span
        className={`
          w-1.5 h-1.5 rounded-full ${style.dot}
          ${style.pulse || status === "loading" ? "animate-pulse-soft" : ""}
        `}
      />
      {displayLabel}
    </span>
  );
}
