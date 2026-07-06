import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, MaterialDetail as MD } from "../api";
import { Badge, Button, Card, Empty, Spinner } from "../components/ui";
import { Markdown } from "../components/Markdown";

export default function MaterialDetail() {
  const { id } = useParams();
  const [m, setM] = useState<MD | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");

  const load = useCallback(() => {
    api.get<MD>(`/api/materials/${id}`).then(setM);
  }, [id]);
  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!m || m.status !== "processing") return;
    const t = setInterval(load, 2500);
    return () => clearInterval(t);
  }, [m, load]);

  if (!m) return <Spinner />;

  const saveText = async (pageId: number) => {
    await api.put(`/api/materials/pages/${pageId}`, { ocr_text: draft });
    setEditing(null);
    load();
  };

  const reocr = async (pageId: number) => {
    await api.post(`/api/materials/pages/${pageId}/reocr`);
    load();
  };

  return (
    <div className="space-y-5">
      <Link to="/materials" className="text-sm text-indigo-600">
        ← 教材一覧
      </Link>
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">{m.title}</h1>
        <Badge status={m.status} />
      </div>
      {m.error && <div className="text-sm text-red-600">{m.error}</div>}
      {m.status === "processing" && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Spinner /> 文字起こし中…（自動更新されます）
        </div>
      )}

      {m.pages.length === 0 ? (
        <Empty>ページがありません</Empty>
      ) : (
        <div className="space-y-6">
          {m.pages.map((p) => (
            <Card key={p.id}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">ページ {p.page_no}</span>
                  <Badge status={p.status} />
                </div>
                <div className="flex gap-2">
                  {editing === p.id ? (
                    <>
                      <Button onClick={() => saveText(p.id)}>保存</Button>
                      <Button
                        variant="ghost"
                        onClick={() => setEditing(null)}
                      >
                        取消
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        variant="secondary"
                        onClick={() => {
                          setEditing(p.id);
                          setDraft(p.ocr_text);
                        }}
                      >
                        編集
                      </Button>
                      <Button variant="ghost" onClick={() => reocr(p.id)}>
                        再OCR
                      </Button>
                    </>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <img
                  src={`/api/materials/${m.id}/pages/${p.page_no}/image`}
                  alt={`page ${p.page_no}`}
                  className="w-full rounded-lg border border-slate-200"
                />
                <div className="min-w-0">
                  {editing === p.id ? (
                    <textarea
                      className="w-full h-full min-h-64 border border-slate-300 rounded-lg p-3 text-sm font-mono"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                    />
                  ) : p.status === "error" ? (
                    <div className="text-sm text-red-600">{p.error}</div>
                  ) : p.ocr_text ? (
                    <Markdown>{p.ocr_text}</Markdown>
                  ) : (
                    <div className="text-sm text-slate-400">（未処理）</div>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
