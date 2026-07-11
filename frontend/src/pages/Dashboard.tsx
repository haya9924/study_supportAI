import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Dashboard as DashboardData } from "../api";
import { Card, Badge, Empty } from "../components/ui";

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    api.get<DashboardData>("/api/dashboard").then(setData);
  }, []);

  if (!data) return <Empty>読み込み中…</Empty>;

  const stats = [
    { label: "今日の復習", value: data.due_today, accent: "text-indigo-600" },
    { label: "新規カード", value: data.new_cards, accent: "text-emerald-600" },
    {
      label: "本日学習済",
      value: data.reviewed_today,
      accent: "text-slate-700 dark:text-slate-200",
    },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">ホーム</h1>

      <div className="grid grid-cols-3 gap-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <div className="text-sm text-slate-500 dark:text-slate-400">
            {s.label}
          </div>
            <div className={`text-3xl font-bold mt-1 ${s.accent}`}>{s.value}</div>
          </Card>
        ))}
      </div>

      {(data.due_today > 0 || data.new_cards > 0) && (
        <Card className="bg-indigo-50 border-indigo-200 dark:bg-indigo-950 dark:border-indigo-900">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-semibold">復習の時間です</div>
              <div className="text-sm text-slate-600 dark:text-slate-300">
                期限到来 {data.due_today} 枚・新規 {data.new_cards} 枚
              </div>
            </div>
            <Link
              to="/decks"
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium"
            >
              フラッシュカードへ
            </Link>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "教材", value: data.counts.materials },
          { label: "デッキ", value: data.counts.decks },
          { label: "カード", value: data.counts.cards },
          { label: "クイズ", value: data.counts.quizzes },
        ].map((c) => (
          <Card key={c.label} className="text-center">
            <div className="text-2xl font-bold">{c.value}</div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              {c.label}
            </div>
          </Card>
        ))}
      </div>

      <div>
        <h2 className="font-semibold mb-2">最近の教材</h2>
        {data.recent_materials.length === 0 ? (
          <Empty>まだ教材がありません</Empty>
        ) : (
          <div className="space-y-2">
            {data.recent_materials.map((m) => (
              <Link
                key={m.id}
                to={`/materials/${m.id}`}
                className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-4 py-3 hover:bg-slate-50 dark:bg-slate-800 dark:border-slate-700 dark:hover:bg-slate-700"
              >
                <span className="truncate">{m.title}</span>
                <Badge status={m.status} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
