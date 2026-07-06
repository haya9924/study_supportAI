import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, DeckStats } from "../api";
import { Button, Card, Empty } from "../components/ui";

export default function Decks() {
  const [decks, setDecks] = useState<DeckStats[]>([]);
  const [name, setName] = useState("");

  const load = () => api.get<DeckStats[]>("/api/decks").then(setDecks);
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!name.trim()) return;
    await api.post("/api/decks", { name });
    setName("");
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

      {decks.length === 0 ? (
        <Empty>デッキがありません。作成して教材からカードを生成しましょう。</Empty>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {decks.map((d) => (
            <Card key={d.id}>
              <div className="flex items-start justify-between">
                <Link
                  to={`/decks/${d.id}`}
                  className="font-semibold hover:text-indigo-600"
                >
                  {d.name}
                </Link>
                <Button variant="ghost" onClick={() => remove(d.id)}>
                  削除
                </Button>
              </div>
              <div className="flex gap-4 mt-3 text-sm">
                <span className="text-slate-500">全 {d.total} 枚</span>
                <span className="text-indigo-600 font-medium">
                  復習 {d.due_count}
                </span>
                <span className="text-emerald-600 font-medium">
                  新規 {d.new_count}
                </span>
              </div>
              <div className="flex gap-2 mt-4">
                <Link
                  to={`/decks/${d.id}/review`}
                  className={`px-4 py-2 rounded-lg text-sm font-medium ${
                    d.due_count + d.new_count > 0
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-100 text-slate-400 pointer-events-none"
                  }`}
                >
                  学習する
                </Link>
                <Link
                  to={`/decks/${d.id}`}
                  className="px-4 py-2 rounded-lg bg-slate-200 text-slate-700 text-sm font-medium"
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
