import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, DeckStats } from "../api";
import { Button, Card, Empty } from "../components/ui";

export default function Decks() {
  const [decks, setDecks] = useState<DeckStats[]>([]);
  const [name, setName] = useState("");
  const [renaming, setRenaming] = useState<number | null>(null);
  const [renameVal, setRenameVal] = useState("");
  const skipBlur = useRef(false);
  // デフォルトの1日の出題枚数(新規カード)
  const [defaultNpd, setDefaultNpd] = useState("");
  const [savedNpd, setSavedNpd] = useState(false);

  const load = () => api.get<DeckStats[]>("/api/decks").then(setDecks);
  useEffect(() => {
    load();
    api
      .get<{ new_per_day: string }>("/api/settings")
      .then((s) => setDefaultNpd(s.new_per_day));
  }, []);

  const saveDefault = async () => {
    await api.put("/api/settings", { new_per_day: defaultNpd });
    setSavedNpd(true);
    setTimeout(() => setSavedNpd(false), 2000);
    load(); // 実効枚数の表示を更新
  };

  const create = async () => {
    if (!name.trim()) return;
    await api.post("/api/decks", { name });
    setName("");
    load();
  };

  const startRename = (d: DeckStats) => {
    setRenaming(d.id);
    setRenameVal(d.name);
  };

  const saveRename = async (id: number) => {
    const v = renameVal.trim();
    if (v) await api.put(`/api/decks/${id}`, { name: v });
    setRenaming(null);
    load();
  };

  const remove = async (id: number) => {
    if (!confirm("このデッキを削除しますか？")) return;
    await api.del(`/api/decks/${id}`);
    load();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">フラッシュカード</h1>

      <Card>
        <div className="flex gap-2">
          <input
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="新しいデッキ名"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && create()}
          />
          <Button onClick={create}>作成</Button>
        </div>
      </Card>

      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium">
            デフォルトの出題枚数（1日の新規カード数）
          </label>
          <input
            type="number"
            min={0}
            className="w-24 border border-slate-300 rounded-lg px-3 py-2 text-sm"
            value={defaultNpd}
            onChange={(e) => setDefaultNpd(e.target.value)}
          />
          <Button variant="secondary" onClick={saveDefault}>
            保存
          </Button>
          {savedNpd && (
            <span className="text-sm text-emerald-600 dark:text-emerald-400">
              保存しました
            </span>
          )}
          <span className="text-xs text-slate-400">
            各デッキで「デフォルトに従う」設定のときに適用されます
          </span>
        </div>
      </Card>

      {decks.length === 0 ? (
        <Empty>デッキがありません。作成して教材からカードを生成しましょう。</Empty>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {decks.map((d) => (
            <Card key={d.id}>
              <div className="flex items-start justify-between gap-2">
                {renaming === d.id ? (
                  <input
                    autoFocus
                    className="flex-1 min-w-0 border border-slate-300 rounded px-2 py-1 text-sm font-semibold"
                    value={renameVal}
                    onChange={(e) => setRenameVal(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                      else if (e.key === "Escape") {
                        skipBlur.current = true;
                        setRenaming(null);
                      }
                    }}
                    onBlur={() => {
                      if (skipBlur.current) {
                        skipBlur.current = false;
                        return;
                      }
                      saveRename(d.id);
                    }}
                  />
                ) : (
                  <div className="flex items-center gap-1 min-w-0">
                    <Link
                      to={`/decks/${d.id}`}
                      className="font-semibold truncate hover:text-indigo-600 dark:hover:text-indigo-400"
                    >
                      {d.name}
                    </Link>
                    <button
                      title="名前を変更"
                      onClick={() => startRename(d)}
                      className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 text-sm px-1 flex-shrink-0"
                    >
                      ✏️
                    </button>
                  </div>
                )}
                <Button variant="ghost" onClick={() => remove(d.id)}>
                  削除
                </Button>
              </div>
              <div className="flex gap-4 mt-3 text-sm">
                <span className="text-slate-500 dark:text-slate-400">
                  全 {d.total} 枚
                </span>
                <span className="text-indigo-600 dark:text-indigo-400 font-medium">
                  復習 {d.due_count}
                </span>
                <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                  新規 {d.new_count}
                </span>
              </div>
              <div className="mt-1 text-xs text-slate-400">
                1日の出題枚数: {d.effective_new_per_day} 枚
                {d.new_per_day === 0 ? "（デフォルト）" : "（個別設定）"}
              </div>
              <div className="flex gap-2 mt-4">
                <Link
                  to={`/decks/${d.id}/review`}
                  className={`px-4 py-2 rounded-lg text-sm font-medium ${
                    d.due_count + d.new_count > 0
                      ? "bg-indigo-600 text-white dark:bg-indigo-500"
                      : "bg-slate-100 text-slate-400 pointer-events-none dark:bg-slate-700 dark:text-slate-500"
                  }`}
                >
                  学習する
                </Link>
                <Link
                  to={`/decks/${d.id}`}
                  className="px-4 py-2 rounded-lg bg-slate-200 text-slate-700 text-sm font-medium dark:bg-slate-700 dark:text-slate-200"
                >
                  管理
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
