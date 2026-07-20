// バックグラウンドタスク管理。
// 生成処理(予想問題・フラッシュカード)を非ブロッキングで実行し、
// 画面遷移しても進捗を下部ポップアップで表示し続ける。
import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import { Link } from "react-router-dom";
import { Spinner } from "./components/ui";

export interface BgTask {
  id: string;
  kind: string; // "exam" | "flashcards"
  label: string;
  status: "running" | "done" | "error";
  meta?: Record<string, unknown>;
  result?: unknown;
  link?: string;
  linkLabel?: string;
  doneLabel?: string;
  // リンク押下でタスクを消さない (遷移先のページが結果を取り込む場合に使う)
  keepOnClick?: boolean;
  error?: string;
}

interface StartOpts {
  kind: string;
  label: string;
  meta?: Record<string, unknown>;
  run: () => Promise<{
    result?: unknown;
    link?: string;
    linkLabel?: string;
    doneLabel?: string;
    keepOnClick?: boolean;
  }>;
}

interface Ctx {
  tasks: BgTask[];
  start: (opts: StartOpts) => void;
  dismiss: (id: string) => void;
}

const TasksContext = createContext<Ctx | null>(null);

export function useTasks(): Ctx {
  const c = useContext(TasksContext);
  if (!c) throw new Error("useTasks は TasksProvider の内側で使ってください");
  return c;
}

let seq = 0;

export function TasksProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<BgTask[]>([]);

  const dismiss = useCallback((id: string) => {
    setTasks((ts) => ts.filter((t) => t.id !== id));
  }, []);

  const start = useCallback((opts: StartOpts) => {
    const id = `t${Date.now()}_${seq++}`;
    setTasks((ts) => [
      ...ts,
      { id, kind: opts.kind, label: opts.label, meta: opts.meta, status: "running" },
    ]);
    opts.run().then(
      (r) =>
        setTasks((ts) =>
          ts.map((t) => (t.id === id ? { ...t, status: "done", ...r } : t))
        ),
      (e: unknown) =>
        setTasks((ts) =>
          ts.map((t) =>
            t.id === id
              ? { ...t, status: "error", error: (e as Error)?.message || String(e) }
              : t
          )
        )
    );
  }, []);

  return (
    <TasksContext.Provider value={{ tasks, start, dismiss }}>
      {children}
    </TasksContext.Provider>
  );
}

export function TasksPopup() {
  const { tasks, dismiss } = useTasks();
  if (tasks.length === 0) return null;
  return (
    <div className="fixed bottom-4 right-4 z-50 w-72 space-y-2 no-print">
      {tasks.map((t) => (
        <div
          key={t.id}
          className="flex items-start gap-3 bg-white border border-slate-200 rounded-lg shadow-lg px-4 py-3 text-sm dark:bg-slate-800 dark:border-slate-700"
        >
          <div className="mt-0.5">
            {t.status === "running" && <Spinner />}
            {t.status === "done" && <span>✅</span>}
            {t.status === "error" && <span>⚠️</span>}
          </div>
          <div className="flex-1 min-w-0">
            {t.status === "running" && <div className="truncate">{t.label}</div>}
            {t.status === "done" && (
              <div>
                <div className="truncate">{t.doneLabel || "完了しました"}</div>
                {t.link && (
                  <Link
                    to={t.link}
                    onClick={() => {
                      if (!t.keepOnClick) dismiss(t.id);
                    }}
                    className="text-indigo-600 dark:text-indigo-400 font-medium"
                  >
                    {t.linkLabel || "開く"}
                  </Link>
                )}
              </div>
            )}
            {t.status === "error" && (
              <div>
                <div>失敗しました</div>
                <div className="text-xs text-red-500 truncate">{t.error}</div>
              </div>
            )}
          </div>
          {t.status !== "running" && (
            <button
              onClick={() => dismiss(t.id)}
              className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
              title="閉じる"
            >
              ✕
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
