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
    primary: "bg-indigo-600 hover:bg-indigo-700 text-white",
    secondary: "bg-slate-200 hover:bg-slate-300 text-slate-800",
    danger: "bg-red-100 hover:bg-red-200 text-red-700",
    ghost: "hover:bg-slate-100 text-slate-600",
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
      className={`bg-white rounded-xl border border-slate-200 shadow-sm p-5 ${className}`}
    >
      {children}
    </div>
  );
}

export function Badge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ready: "bg-emerald-100 text-emerald-700",
    done: "bg-emerald-100 text-emerald-700",
    processing: "bg-amber-100 text-amber-700",
    pending: "bg-slate-100 text-slate-600",
    uploaded: "bg-slate-100 text-slate-600",
    error: "bg-red-100 text-red-700",
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
    <span className="inline-block w-4 h-4 border-2 border-slate-300 border-t-indigo-600 rounded-full animate-spin" />
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="text-center text-slate-400 py-12 text-sm">{children}</div>
  );
}
