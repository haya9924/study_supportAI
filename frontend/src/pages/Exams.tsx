import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, Exam } from "../api";
import { Button, Card, Empty, Spinner } from "../components/ui";
import { MaterialPicker, Selection } from "../components/MaterialPicker";

export default function Exams() {
  const nav = useNavigate();
  const [exams, setExams] = useState<Exam[]>([]);
  const [sel, setSel] = useState<Selection>({ courseId: null, materialIds: [] });
  const [title, setTitle] = useState("");
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.get<Exam[]>("/api/exams").then(setExams);
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    setBusy(true);
    try {
      const e = await api.post<Exam>("/api/exams", {
        course_id: sel.courseId,
        material_ids: sel.materialIds,
        instruction,
        title: title || "予想問題",
      });
      nav(`/exams/${e.id}`);
    } catch (err) {
      alert("生成失敗: " + (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    if (!confirm("削除しますか？")) return;
    await api.del(`/api/exams/${id}`);
    load();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">予想問題</h1>

      <Card>
        <h2 className="font-semibold mb-3">過去問・資料から予想問題を作成</h2>
        <MaterialPicker value={sel} onChange={setSel} />
        <div className="grid grid-cols-2 gap-3 mt-3">
          <input
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="タイトル"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <input
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="指示（例: 記述式中心で難易度高め）"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
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
        <h2 className="font-semibold mb-2">予想問題一覧</h2>
        {exams.length === 0 ? (
          <Empty>まだありません</Empty>
        ) : (
          <div className="space-y-2">
            {exams.map((e) => (
              <div
                key={e.id}
                className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-4 py-3"
              >
                <Link
                  to={`/exams/${e.id}`}
                  className="font-medium hover:text-indigo-600"
                >
                  {e.title}
                </Link>
                <Button variant="ghost" onClick={() => remove(e.id)}>
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
