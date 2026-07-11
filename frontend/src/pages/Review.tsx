import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ReviewCard } from "../api";
import { Button, Empty, Spinner } from "../components/ui";
import { Markdown } from "../components/Markdown";

const RATING = [
  { r: 1, label: "もう一度", color: "bg-red-500 hover:bg-red-600" },
  { r: 2, label: "難しい", color: "bg-orange-500 hover:bg-orange-600" },
  { r: 3, label: "普通", color: "bg-emerald-500 hover:bg-emerald-600" },
  { r: 4, label: "簡単", color: "bg-sky-500 hover:bg-sky-600" },
];

export default function Review() {
  const { id } = useParams();
  const deckId = Number(id);
  const [state, setState] = useState<ReviewCard | null>(null);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(true);
  const busy = useRef(false);

  const load = useCallback(() => {
    setLoading(true);
    api.get<ReviewCard>(`/api/decks/${deckId}/next`).then((r) => {
      setState(r);
      setFlipped(false);
      setLoading(false);
    });
  }, [deckId]);
  useEffect(() => {
    load();
  }, [load]);

  const rate = useCallback(
    async (rating: number) => {
      if (!state?.card || busy.current) return;
      busy.current = true;
      setLoading(true);
      try {
        const next = await api.post<ReviewCard>(
          `/api/decks/cards/${state.card.id}/review`,
          { rating }
        );
        setState(next);
        setFlipped(false);
      } finally {
        setLoading(false);
        busy.current = false;
      }
    },
    [state]
  );

  // PC のキーボード操作: 表面 Space/Enter でめくる、裏面 1〜4 で回答
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;
      if (!state?.card) return;
      if (!flipped) {
        if (e.code === "Space" || e.key === "Enter") {
          e.preventDefault();
          setFlipped(true);
        }
        return;
      }
      const n = Number(e.key);
      if (n >= 1 && n <= 4) {
        e.preventDefault();
        rate(n);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [flipped, state, rate]);

  if (loading && !state) return <Spinner />;

  if (!state?.card) {
    return (
      <div className="space-y-4">
        <Link to="/decks" className="text-sm text-indigo-600 dark:text-indigo-400">
          ← フラッシュカード
        </Link>
        <Empty>
          🎉 今日の学習は完了です！<br />
          期限が来たカードはまた表示されます。
        </Empty>
      </div>
    );
  }

  const card = state.card;

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="flex items-center justify-between no-print">
        <Link to="/decks" className="text-sm text-indigo-600 dark:text-indigo-400">
          ← 中断して戻る
        </Link>
        <span className="text-sm text-slate-500 dark:text-slate-400">
          残り {state.remaining} 枚
        </span>
      </div>

      <div
        className="bg-white rounded-2xl border border-slate-200 shadow-sm min-h-72 p-8 flex flex-col cursor-pointer dark:bg-slate-800 dark:border-slate-700"
        onClick={() => !flipped && setFlipped(true)}
      >
        <div className="flex-1 flex items-center justify-center text-center">
          <div className="text-lg">
            <Markdown>{card.front}</Markdown>
          </div>
        </div>
        {flipped && (
          <>
            <hr className="my-4 border-slate-200 dark:border-slate-700" />
            <div className="flex-1 flex items-center justify-center text-center">
              <div className="text-lg text-slate-700 dark:text-slate-200">
                <Markdown>{card.back}</Markdown>
              </div>
            </div>
          </>
        )}
      </div>

      {!flipped ? (
        <Button onClick={() => setFlipped(true)} className="w-full py-3">
          答えを見る
          <span className="hidden sm:inline opacity-70 ml-2 text-xs">
            (Space)
          </span>
        </Button>
      ) : (
        <div className="grid grid-cols-4 gap-2">
          {RATING.map((b) => (
            <button
              key={b.r}
              onClick={() => rate(b.r)}
              disabled={loading}
              className={`relative ${b.color} text-white rounded-lg py-3 text-sm font-medium disabled:opacity-50`}
            >
              <span className="hidden sm:flex absolute top-1 right-1.5 items-center justify-center w-4 h-4 rounded bg-white/25 text-[10px]">
                {b.r}
              </span>
              <div>{b.label}</div>
              <div className="text-xs opacity-90 mt-0.5">
                {state.intervals?.[String(b.r)]}
              </div>
            </button>
          ))}
        </div>
      )}

      <div className="text-center text-xs text-slate-400 no-print">
        {card.is_new && (
          <span className="text-emerald-600 dark:text-emerald-400 mr-2">
            新しいカード
          </span>
        )}
        <span className="hidden sm:inline">
          キーボード: Space で答えを表示 / 1〜4 で回答
        </span>
      </div>
    </div>
  );
}
