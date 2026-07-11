import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, Quiz, QuizDetail } from "../api";
import { Button, Card, Empty, Spinner } from "../components/ui";
import { MaterialPicker, Selection } from "../components/MaterialPicker";

export default function Quizzes() {
  const nav = useNavigate();
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [sel, setSel] = useState<Selection>({ courseId: null, materialIds: [] });
  const [title, setTitle] = useState("");
  const [instruction, setInstruction] = useState("");
  const [count, setCount] = useState(8);
  const [busy, setBusy] = useState(false);

  const load = () => api.get<Quiz[]>("/api/quizzes").then(setQuizzes);
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    setBusy(true);
    try {
      const q = await api.post<QuizDetail>("/api/quizzes", {
        course_id: sel.courseId,
        material_ids: sel.materialIds,
        instruction,
        count,
        title: title || "クイズ",
      });
      nav(`/quizzes/${q.id}`);
    } catch (e) {
      alert("生成失敗: " + (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    if (!confirm("削除しますか？")) return;
    await api.del(`/api/quizzes/${id}`);
    load();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">クイズ</h1>

      <Card>
        <h2 className="font-semibold mb-3">教材からクイズを生成</h2>
        <MaterialPicker value={sel} onChange={setSel} />
        <div className="grid grid-cols-3 gap-3 mt-3">
          <input
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="タイトル"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <input
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="追加指示（任意）"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
          />
          <input
            type="number"
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
          />
        </div>
        <div className="mt-3 flex items-center gap-3">
          <Button onClick={create} disabled={busy}>
            {busy ? "生成中…" : "生成する"}
          </Button>
          {busy && <Spinner />}
        </div>
      </Card>

      <div>
        <h2 className="font-semibold mb-2">クイズ一覧</h2>
        {quizzes.length === 0 ? (
          <Empty>まだクイズがありません</Empty>
        ) : (
          <div className="space-y-2">
            {quizzes.map((q) => (
              <div
                key={q.id}
                className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-4 py-3 dark:bg-slate-800 dark:border-slate-700"
              >
                <Link
                  to={`/quizzes/${q.id}`}
                  className="font-medium hover:text-indigo-600"
                >
                  {q.title}
                </Link>
                <Button variant="ghost" onClick={() => remove(q.id)}>
                  削除
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
