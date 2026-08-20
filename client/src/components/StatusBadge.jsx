import React from "react";
import Badge from "./ui/Badge";

const STATUS_STYLES = {
  // API health statuses
  ok: {
    variant: "success",
    label: "Connected",
  },
  degraded: {
    variant: "warning",
    label: "Degraded",
  },
  error: {
    variant: "warning", // Or error
    label: "Error",
  },
  loading: {
    variant: "default",
    label: "Checking...",
  },

  // Repository mining statuses
  pending: {
    variant: "info",
    label: "Pending",
    pulse: true,
  },
  cloning: {
    variant: "info",
    label: "Cloning...",
    pulse: true,
  },
  mining: {
    variant: "primary",
    label: "Mining Git log...",
    pulse: true,
  },
  ready: {
    variant: "success",
    label: "Ready",
  },
};

export default function StatusBadge({ status = "loading", label }) {
  const style = STATUS_STYLES[status] || {
    variant: "default",
    label: status,
  };
  const displayLabel = label || style.label;

  return (
    <Badge variant={style.variant} className={style.pulse ? "animate-pulse" : ""}>
      {displayLabel}
    </Badge>
  );
}
