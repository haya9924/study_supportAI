import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Card as CardType, CardDraft } from "../api";
import { Button, Card, Empty } from "../components/ui";
import { MaterialPicker, Selection } from "../components/MaterialPicker";
import { useTasks } from "../tasks";

export default function DeckDetail() {
  const { id } = useParams();
  const deckId = Number(id);
  const { start, tasks, dismiss } = useTasks();
  const [cards, setCards] = useState<CardType[]>([]);
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");

  // 生成
  const [sel, setSel] = useState<Selection>({ courseId: null, materialIds: [] });
  const [instruction, setInstruction] = useState("");
  const [count, setCount] = useState(15);
  const [drafts, setDrafts] = useState<CardDraft[] | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());

  // このデッキ宛ての生成タスクが走っているか
  const generating = tasks.some(
    (t) =>
      t.kind === "flashcards" &&
      t.status === "running" &&
      t.meta?.deckId === deckId
  );

  const load = useCallback(() => {
    api.get<CardType[]>(`/api/decks/${deckId}/cards`).then(setCards);
  }, [deckId]);
  useEffect(() => {
    load();
  }, [load]);

  // このデッキ宛ての生成タスクが完了したら候補を取り込む
  useEffect(() => {
    const done = tasks.find(
      (t) =>
        t.kind === "flashcards" &&
        t.status === "done" &&
        t.meta?.deckId === deckId
    );
    if (done) {
      const d = (done.result as { drafts: CardDraft[] }).drafts;
      setDrafts(d);
      setPicked(new Set(d.map((_, i) => i)));
      dismiss(done.id);
    }
  }, [tasks, deckId, dismiss]);

  const addManual = async () => {
    if (!front.trim() || !back.trim()) return;
    await api.post(`/api/decks/${deckId}/cards`, { front, back });
    setFront("");
    setBack("");
    load();
  };

  const removeCard = async (cid: number) => {
    if (!confirm("このカードを削除しますか？")) return;
    await api.del(`/api/decks/cards/${cid}`);
    load();
  };

  const generate = () => {
    setDrafts(null);
    start({
      kind: "flashcards",
      label: "カード候補を作成中…",
      meta: { deckId },
      run: async () => {
        const res = await api.post<CardDraft[]>("/api/generate/flashcards", {
          course_id: sel.courseId,
          material_ids: sel.materialIds,
          instruction,
          count,
        });
        return {
          result: { deckId, drafts: res },
          link: `/decks/${deckId}`,
          linkLabel: "確認",
          doneLabel: `カード候補が ${res.length} 件できました`,
          keepOnClick: true, // デッキ画面側で取り込む
        };
      },
    });
  };

  const saveDrafts = async () => {
    if (!drafts) return;
    const chosen = drafts.filter((_, i) => picked.has(i));
    await api.post(`/api/decks/${deckId}/cards/bulk`, { cards: chosen });
    setDrafts(null);
    load();
  };

  const togglePick = (i: number) => {
    const s = new Set(picked);
    if (s.has(i)) s.delete(i);
    else s.add(i);
    setPicked(s);
  };

  return (
    <div className="space-y-6">
      <Link to="/decks" className="text-sm text-indigo-600">
        ← フラッシュカード
      </Link>

      <Card>
        <h2 className="font-semibold mb-3">教材からカードを生成</h2>
        <MaterialPicker value={sel} onChange={setSel} />
        <div className="grid grid-cols-3 gap-3 mt-3">
          <div className="col-span-2">
            <label className="block text-sm font-medium mb-1">追加指示（任意）</label>
            <input
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="例: 用語の定義を中心に"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">枚数</label>
            <input
              type="number"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            />
          </div>
        </div>
        <div className="mt-3 flex items-center gap-3">
          <Button onClick={generate} disabled={generating}>
            {generating ? "生成中…" : "生成する"}
          </Button>
          <span className="text-xs text-slate-400">
            生成は裏で実行され、他の画面に移動できます
          </span>
        </div>

        {generating && (
          <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">
            バックグラウンドで作成中です。完了すると候補がここに表示されます。
          </div>
        )}

        {drafts && (
          <div className="mt-4 space-y-2">
            <div className="text-sm text-slate-500">
              {picked.size} / {drafts.length} 枚を選択中
            </div>
            {drafts.map((d, i) => (
              <label
                key={i}
                className="flex gap-3 items-start border border-slate-200 rounded-lg p-3 cursor-pointer hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-700"
              >
                <input
                  type="checkbox"
                  checked={picked.has(i)}
                  onChange={() => togglePick(i)}
                  className="mt-1"
                />
                <div className="text-sm">
                  <div className="font-medium">{d.front}</div>
                  <div className="text-slate-500">{d.back}</div>
                </div>
              </label>
            ))}
            <Button onClick={saveDrafts} disabled={picked.size === 0}>
              選択した {picked.size} 枚をデッキに追加
            </Button>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="font-semibold mb-3">手動でカード追加</h2>
        <div className="grid grid-cols-2 gap-3">
          <textarea
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="表（問い）"
            value={front}
            onChange={(e) => setFront(e.target.value)}
          />
          <textarea
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="裏（答え）"
            value={back}
            onChange={(e) => setBack(e.target.value)}
          />
        </div>
        <div className="mt-3">
          <Button onClick={addManual}>追加</Button>
        </div>
      </Card>

      <div>
        <h2 className="font-semibold mb-2">カード一覧（{cards.length}）</h2>
        {cards.length === 0 ? (
          <Empty>まだカードがありません</Empty>
        ) : (
          <div className="space-y-2">
            {cards.map((c) => (
              <div
                key={c.id}
                className="flex items-start justify-between bg-white border border-slate-200 rounded-lg px-4 py-3 dark:bg-slate-800 dark:border-slate-700"
              >
                <div className="text-sm min-w-0">
                  <div className="font-medium truncate">{c.front}</div>
                  <div className="text-slate-500 truncate">{c.back}</div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs text-slate-400">
                    {c.is_new ? "新規" : `復習${c.reps}回`}
                  </span>
                  <Button variant="ghost" onClick={() => removeCard(c.id)}>
                    削除
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
