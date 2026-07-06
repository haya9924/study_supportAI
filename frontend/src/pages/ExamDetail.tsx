import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Exam } from "../api";
import { Button, Card, Spinner } from "../components/ui";
import { Markdown } from "../components/Markdown";

export default function ExamDetail() {
  const { id } = useParams();
  const examId = Number(id);
  const [exam, setExam] = useState<Exam | null>(null);
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.get<Exam>(`/api/exams/${examId}`).then(setExam);
  }, [examId]);
  useEffect(() => {
    load();
  }, [load]);

  if (!exam) return <Spinner />;

  const revise = async () => {
    if (!instruction.trim()) return;
    setBusy(true);
    try {
      const e = await api.post<Exam>(`/api/exams/${examId}/revise`, {
        instruction,
      });
      setExam(e);
      setInstruction("");
    } catch (err) {
      alert("改訂失敗: " + (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between no-print">
        <Link to="/exams" className="text-sm text-indigo-600">
          ← 予想問題一覧
        </Link>
        <Button variant="secondary" onClick={() => window.print()}>
          印刷 / PDF
        </Button>
      </div>

      <h1 className="text-2xl font-bold">{exam.title}</h1>

      <Card>
        <Markdown>{exam.content_md}</Markdown>
      </Card>

      <Card className="no-print">
        <h2 className="font-semibold mb-2">改訂指示</h2>
        <p className="text-sm text-slate-500 mb-2">
          追加の指示を送ると、内容を踏まえて作り直します。
        </p>
        <textarea
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
          rows={2}
          placeholder="例: 問3をもっと難しくして、計算問題を追加"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
        />
        <div className="mt-2 flex items-center gap-3">
          <Button onClick={revise} disabled={busy}>
            {busy ? "改訂中…" : "改訂する"}
          </Button>
          {busy && <Spinner />}
        </div>
        {exam.messages.filter((m) => m.role === "user").length > 1 && (
          <div className="mt-4 text-xs text-slate-400">
            <div className="font-medium mb-1">指示履歴</div>
            {exam.messages
              .filter((m) => m.role === "user")
              .map((m, i) => (
                <div key={i} className="truncate">
                  ・{m.content}
                </div>
              ))}
          </div>
        )}
      </Card>
    </div>
  );
}
