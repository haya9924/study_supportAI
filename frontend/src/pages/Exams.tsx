import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Exam } from "../api";
import { Button, Card, Empty } from "../components/ui";
import { MaterialPicker, Selection } from "../components/MaterialPicker";
import { useTasks } from "../tasks";

export default function Exams() {
  const { start, tasks } = useTasks();
  const [exams, setExams] = useState<Exam[]>([]);
  const [sel, setSel] = useState<Selection>({ courseId: null, materialIds: [] });
  const [title, setTitle] = useState("");
  const [instruction, setInstruction] = useState("");

  const load = () => api.get<Exam[]>("/api/exams").then(setExams);
  useEffect(() => {
    load();
  }, []);

  // 生成タスクが完了したら一覧を更新
  useEffect(() => {
    if (tasks.some((t) => t.kind === "exam" && t.status === "done")) load();
  }, [tasks]);

  const create = () => {
    const displayTitle = title || "予想問題";
    start({
      kind: "exam",
      label: `予想問題「${displayTitle}」を作成中…`,
      run: async () => {
        const e = await api.post<Exam>("/api/exams", {
          course_id: sel.courseId,
          material_ids: sel.materialIds,
          instruction,
          title: displayTitle,
        });
        return {
          result: e,
          link: `/exams/${e.id}`,
          linkLabel: "開く",
          doneLabel: `予想問題「${e.title}」ができました`,
        };
      },
    });
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
          <Button onClick={create}>生成する</Button>
          <span className="text-xs text-slate-400">
            生成は裏で実行され、他の画面に移動できます
          </span>
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
                className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-4 py-3 dark:bg-slate-800 dark:border-slate-700"
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
