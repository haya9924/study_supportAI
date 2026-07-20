import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Exam } from "../api";
import { Button, Card, Spinner } from "../components/ui";
import { Markdown } from "../components/Markdown";

type BoolMap = Record<number, boolean>;

export default function ExamDetail() {
  const { id } = useParams();
  const examId = Number(id);
  const [exam, setExam] = useState<Exam | null>(null);
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [showAns, setShowAns] = useState<BoolMap>({});
  const [showExp, setShowExp] = useState<BoolMap>({});
  const [followInput, setFollowInput] = useState<Record<number, string>>({});
  const [asking, setAsking] = useState<number | null>(null);

  const load = useCallback(() => {
    api.get<Exam>(`/api/exams/${examId}`).then(setExam);
  }, [examId]);
  useEffect(() => {
    load();
  }, [load]);

  if (!exam) return <Spinner />;

  const questions = exam.questions ?? [];
  const structured = questions.length > 0;

  const revise = async () => {
    if (!instruction.trim()) return;
    setBusy(true);
    try {
      const e = await api.post<Exam>(`/api/exams/${examId}/revise`, { instruction });
      setExam(e);
      setInstruction("");
      setShowAns({});
      setShowExp({});
    } catch (err) {
      alert("改訂失敗: " + (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const revealAll = (v: boolean) => {
    const rec: BoolMap = {};
    questions.forEach((_, i) => (rec[i] = v));
    setShowAns(rec);
    setShowExp(rec);
  };

  const ask = async (i: number) => {
    const q = (followInput[i] || "").trim();
    if (!q) return;
    setAsking(i);
    try {
      const e = await api.post<Exam>(`/api/exams/${examId}/questions/${i}/ask`, {
        question: q,
      });
      setExam(e);
      setFollowInput((s) => ({ ...s, [i]: "" }));
    } catch (err) {
      alert("質問に失敗: " + (err as Error).message);
    } finally {
      setAsking(null);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between no-print">
        <Link to="/exams" className="text-sm text-indigo-600 dark:text-indigo-400">
          ← 予想問題一覧
        </Link>
        <div className="flex items-center gap-2">
          {structured && (
            <>
              <Button variant="secondary" onClick={() => revealAll(true)}>
                すべて表示
              </Button>
              <Button variant="ghost" onClick={() => revealAll(false)}>
                すべて隠す
              </Button>
            </>
          )}
          <Button variant="secondary" onClick={() => window.print()}>
            印刷 / PDF
          </Button>
        </div>
      </div>

      <h1 className="text-2xl font-bold">{exam.title}</h1>

      {structured ? (
        <div className="space-y-4">
          {questions.map((q, i) => (
            <Card key={i}>
              <div className="grid lg:grid-cols-2 gap-6">
                {/* 左: 問題 */}
                <div>
                  <div className="text-xs font-semibold text-slate-400 mb-1">
                    問 {i + 1}
                  </div>
                  <Markdown>{q.problem}</Markdown>
                </div>

                {/* 右: 解答・解説・追加質問 */}
                <div className="space-y-4 lg:border-l lg:pl-6 border-slate-200 dark:border-slate-700">
                  {/* 解答 */}
                  <RevealBlock
                    label="解答"
                    accent="text-emerald-600 dark:text-emerald-400"
                    shown={!!showAns[i]}
                    onToggle={() =>
                      setShowAns((s) => ({ ...s, [i]: !s[i] }))
                    }
                  >
                    {q.answer}
                  </RevealBlock>

                  {/* 解説 */}
                  <RevealBlock
                    label="解説"
                    accent="text-indigo-600 dark:text-indigo-400"
                    shown={!!showExp[i]}
                    onToggle={() =>
                      setShowExp((s) => ({ ...s, [i]: !s[i] }))
                    }
                  >
                    {q.explanation}
                  </RevealBlock>

                  {/* 追加質問 */}
                  <div className="pt-3 border-t border-slate-100 dark:border-slate-700">
                    <div className="text-xs font-semibold text-slate-400 mb-2">
                      この問題について質問する
                    </div>
                    {q.followups?.length > 0 && (
                      <div className="space-y-2 mb-2">
                        {q.followups.map((f, k) => (
                          <div
                            key={k}
                            className={`rounded-lg px-3 py-2 text-sm ${
                              f.role === "user"
                                ? "bg-slate-100 dark:bg-slate-700"
                                : "bg-indigo-50 dark:bg-indigo-950"
                            }`}
                          >
                            <div className="text-[10px] text-slate-400 mb-0.5">
                              {f.role === "user" ? "質問" : "回答"}
                            </div>
                            <Markdown>{f.content}</Markdown>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="flex gap-2 no-print">
                      <input
                        className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm"
                        placeholder="例: なぜこの解答になるの？"
                        value={followInput[i] || ""}
                        onChange={(e) =>
                          setFollowInput((s) => ({ ...s, [i]: e.target.value }))
                        }
                        onKeyDown={(e) => e.key === "Enter" && ask(i)}
                        disabled={asking === i}
                      />
                      <Button onClick={() => ask(i)} disabled={asking === i}>
                        {asking === i ? "…" : "質問"}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        // 旧形式(構造化前)の予想問題は Markdown をそのまま表示
        <Card>
          <Markdown>{exam.content_md}</Markdown>
        </Card>
      )}

      <Card className="no-print">
        <h2 className="font-semibold mb-2">改訂指示</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">
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

// 解答/解説をボタンで開閉。印刷時は常に表示する。
function RevealBlock({
  label,
  accent,
  shown,
  onToggle,
  children,
}: {
  label: string;
  accent: string;
  shown: boolean;
  onToggle: () => void;
  children: string;
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        className="no-print text-sm px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-100 font-medium"
      >
        {shown ? `${label}を隠す` : `${label}を表示`}
      </button>
      <div className={shown ? "mt-2" : "hidden print:block mt-2"}>
        <div className={`text-xs font-semibold mb-1 ${accent}`}>{label}</div>
        <Markdown>{children}</Markdown>
      </div>
    </div>
  );
}
