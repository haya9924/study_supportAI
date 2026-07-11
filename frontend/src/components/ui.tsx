import { ReactNode } from "react";

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  const styles: Record<string, string> = {
    primary:
      "bg-indigo-600 hover:bg-indigo-700 text-white dark:bg-indigo-500 dark:hover:bg-indigo-400",
    secondary:
      "bg-slate-200 hover:bg-slate-300 text-slate-800 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-100",
    danger:
      "bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-950 dark:hover:bg-red-900 dark:text-red-300",
    ghost:
      "hover:bg-slate-100 text-slate-600 dark:hover:bg-slate-700 dark:text-slate-300",
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`bg-white rounded-xl border border-slate-200 shadow-sm p-5 dark:bg-slate-800 dark:border-slate-700 ${className}`}
    >
      {children}
    </div>
  );
}

export function Badge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ready: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
    done: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
    processing: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
    pending: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    uploaded: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    error: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  };
  const label: Record<string, string> = {
    ready: "完了",
    done: "完了",
    processing: "処理中",
    pending: "待機",
    uploaded: "アップロード済",
    error: "エラー",
  };
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
        map[status] || "bg-slate-100 text-slate-600"
      }`}
    >
      {label[status] || status}
    </span>
  );
}

export function Spinner() {
  return (
    <span className="inline-block w-4 h-4 border-2 border-slate-300 border-t-indigo-600 rounded-full animate-spin dark:border-slate-600 dark:border-t-indigo-400" />
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="text-center text-slate-400 py-12 text-sm dark:text-slate-500">
      {children}
    </div>
  );
}
