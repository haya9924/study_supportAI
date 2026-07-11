import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Attempt, QuizDetail } from "../api";
import { Button, Card, Spinner } from "../components/ui";
import { Markdown } from "../components/Markdown";

interface Feedback {
  correct: boolean;
  feedback: string;
  correct_answer: string;
  explanation: string;
}

export default function QuizTake() {
  const { id } = useParams();
  const quizId = Number(id);
  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [idx, setIdx] = useState(0);
  const [response, setResponse] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [finished, setFinished] = useState<Attempt | null>(null);

  const init = useCallback(async () => {
    const q = await api.get<QuizDetail>(`/api/quizzes/${quizId}`);
    setQuiz(q);
    const a = await api.post<Attempt>(`/api/quizzes/${quizId}/attempt`);
    setAttempt(a);
    // 途中再開: 最初の未解答の設問へジャンプ
    const answered = new Set(Object.keys(a.answers));
    let start = q.questions.findIndex((qq) => !answered.has(String(qq.id)));
    if (start === -1) start = q.questions.length - 1;
    setIdx(start);
  }, [quizId]);

  useEffect(() => {
    init();
  }, [init]);

  if (!quiz || !attempt) return <Spinner />;

  const total = quiz.questions.length;
  const q = quiz.questions[idx];
  const prev = attempt.answers[String(q.id)];

  const submit = async () => {
    if (response === "" && !prev) return;
    setSubmitting(true);
    const res = await api.post<Feedback>(
      `/api/quizzes/attempt/${attempt.id}/answer`,
      { question_id: q.id, response }
    );
    setFeedback(res);
    // ローカル attempt.answers も更新
    setAttempt({
      ...attempt,
      answers: {
        ...attempt.answers,
        [String(q.id)]: {
          response,
          correct: res.correct,
          feedback: res.feedback,
          correct_answer: res.correct_answer,
          type: q.type,
        },
      },
    });
    setSubmitting(false);
  };

  const next = () => {
    setFeedback(null);
    setResponse("");
    if (idx < total - 1) setIdx(idx + 1);
  };

  const finish = async () => {
    const done = await api.post<Attempt>(
      `/api/quizzes/attempt/${attempt.id}/finish`
    );
    setFinished(done);
  };

  if (finished) {
    return (
      <div className="max-w-2xl mx-auto space-y-5">
        <Link to="/quizzes" className="text-sm text-indigo-600">
          ← クイズ一覧
        </Link>
        <Card className="text-center">
          <div className="text-sm text-slate-500">スコア</div>
          <div className="text-5xl font-bold text-indigo-600 my-2">
            {Math.round(finished.score)}
            <span className="text-lg text-slate-400"> / 100</span>
          </div>
        </Card>
        <div className="space-y-3">
          {quiz.questions.map((qq, i) => {
            const a = finished.answers[String(qq.id)];
            return (
              <Card key={qq.id}>
                <div className="flex items-start gap-2">
                  <span>{a?.correct ? "⭕" : "❌"}</span>
                  <div className="flex-1">
                    <div className="font-medium text-sm">
                      {i + 1}. {qq.question}
                    </div>
                    <div className="text-sm text-slate-600 mt-1">
                      あなたの解答: {formatResp(qq, a?.response)}
                    </div>
                    <div className="text-sm text-emerald-700">
                      正解: {formatAnswer(qq, a?.correct_answer)}
                    </div>
                    {a?.feedback && (
                      <div className="text-xs text-slate-500 mt-1">
                        {a.feedback}
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    );
  }

  const allAnswered = quiz.questions.every(
    (qq) => attempt.answers[String(qq.id)]
  );

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <Link to="/quizzes" className="text-sm text-indigo-600">
          ← 中断（解答は保存済み）
        </Link>
        <span className="text-sm text-slate-500">
          {idx + 1} / {total}
        </span>
      </div>

      <Card>
        <div className="text-xs text-slate-400 mb-2">
          {typeLabel(q.type)}
        </div>
        <div className="font-medium mb-4">
          <Markdown>{q.question}</Markdown>
        </div>

        <QuestionInput
          type={q.type}
          choices={q.choices}
          value={response || prev?.response || ""}
          disabled={!!feedback}
          onChange={setResponse}
        />

        {feedback && (
          <div
            className={`mt-4 rounded-lg p-3 text-sm ${
              feedback.correct
                ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
                : "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200"
            }`}
          >
            <div className="font-medium">
              {feedback.correct ? "⭕ 正解" : "❌ 不正解"}
            </div>
            <div className="mt-1">
              正解: {formatAnswer(q, feedback.correct_answer)}
            </div>
            {feedback.explanation && (
              <div className="mt-1 text-slate-600">{feedback.explanation}</div>
            )}
          </div>
        )}

        <div className="mt-4 flex gap-2">
          {!feedback ? (
            <Button onClick={submit} disabled={submitting}>
              {submitting ? "採点中…" : "解答する"}
            </Button>
          ) : idx < total - 1 ? (
            <Button onClick={next}>次の問題</Button>
          ) : (
            <Button onClick={finish}>結果を見る</Button>
          )}
          {allAnswered && !feedback && (
            <Button variant="secondary" onClick={finish}>
              結果を見る
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

function QuestionInput({
  type,
  choices,
  value,
  disabled,
  onChange,
}: {
  type: string;
  choices: string[];
  value: string;
  disabled: boolean;
  onChange: (v: string) => void;
}) {
  if (type === "mcq") {
    return (
      <div className="space-y-2">
        {choices.map((c, i) => (
          <label
            key={i}
            className={`flex items-center gap-2 border rounded-lg px-3 py-2 text-sm cursor-pointer ${
              value === String(i)
                ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950"
                : "border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-700"
            }`}
          >
            <input
              type="radio"
              checked={value === String(i)}
              disabled={disabled}
              onChange={() => onChange(String(i))}
            />
            {c}
          </label>
        ))}
      </div>
    );
  }
  if (type === "tf") {
    return (
      <div className="flex gap-2">
        {[
          { v: "true", label: "正しい（○）" },
          { v: "false", label: "誤り（×）" },
        ].map((o) => (
          <label
            key={o.v}
            className={`flex-1 flex items-center justify-center gap-2 border rounded-lg px-3 py-3 text-sm cursor-pointer ${
              value === o.v
                ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950"
                : "border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-700"
            }`}
          >
            <input
              type="radio"
              checked={value === o.v}
              disabled={disabled}
              onChange={() => onChange(o.v)}
            />
            {o.label}
          </label>
        ))}
      </div>
    );
  }
  return (
    <textarea
      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
      rows={3}
      placeholder="解答を入力"
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function typeLabel(t: string) {
  return { mcq: "選択式", tf: "正誤問題", short: "短答" }[t] || t;
}

function formatResp(
  q: { type: string; choices: string[] },
  resp: string | undefined
) {
  if (resp == null || resp === "") return "（未解答）";
  return formatAnswer(q, resp);
}

function formatAnswer(
  q: { type: string; choices: string[] },
  ans: string | undefined
) {
  if (ans == null) return "";
  if (q.type === "mcq") {
    const i = Number(ans);
    return q.choices[i] ?? ans;
  }
  if (q.type === "tf") return ans === "true" ? "正しい（○）" : "誤り（×）";
  return ans;
}
