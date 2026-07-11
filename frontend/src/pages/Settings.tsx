import { useEffect, useState } from "react";
import { api, SettingsData } from "../api";
import { Button, Card, Spinner } from "../components/ui";

export default function Settings() {
  const [s, setS] = useState<SettingsData | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const load = () => api.get<SettingsData>("/api/settings").then(setS);
  useEffect(() => {
    load();
  }, []);

  if (!s) return <Spinner />;

  const update = (patch: Partial<SettingsData>) =>
    setS({ ...s, ...patch });

  const save = async () => {
    await api.put("/api/settings", {
      api_base_url: s.api_base_url,
      api_key: apiKey || undefined,
      vision_model: s.vision_model,
      text_model: s.text_model,
      new_per_day: s.new_per_day,
      desired_retention: s.desired_retention,
      context_char_budget: s.context_char_budget,
    });
    setApiKey("");
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    load();
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.post<{ ok: boolean; count: number }>(
        "/api/settings/test"
      );
      setTestResult(`✅ 接続成功（モデル ${r.count} 件）`);
    } catch (e) {
      setTestResult(`❌ ${(e as Error).message}`);
    } finally {
      setTesting(false);
    }
  };

  const field = "w-full border border-slate-300 rounded-lg px-3 py-2 text-sm";
  const label = "block text-sm font-medium mb-1 mt-3";

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">設定</h1>

      {s.llm_mock && (
        <Card className="bg-amber-50 border-amber-200 text-sm text-amber-800 dark:bg-amber-950 dark:border-amber-900 dark:text-amber-200">
          現在 <b>モックモード</b>（LLM_MOCK=1）で動作中です。外部 API には接続せず
          ダミー応答を返します。
        </Card>
      )}

      <Card>
        <h2 className="font-semibold mb-2">LLM 接続（OpenAI 互換 API）</h2>
        <label className={label}>ベース URL</label>
        <input
          className={field}
          value={s.api_base_url}
          onChange={(e) => update({ api_base_url: e.target.value })}
          placeholder="https://openrouter.ai/api/v1"
        />
        <label className={label}>API キー</label>
        <input
          className={field}
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={s.api_key_set ? "（設定済み・変更する場合のみ入力）" : "sk-..."}
        />
        <label className={label}>Vision モデル（OCR 用・画像対応）</label>
        <input
          className={field}
          value={s.vision_model}
          onChange={(e) => update({ vision_model: e.target.value })}
          placeholder="google/gemini-2.5-flash"
        />
        <label className={label}>テキストモデル（問題・カード生成用）</label>
        <input
          className={field}
          value={s.text_model}
          onChange={(e) => update({ text_model: e.target.value })}
          placeholder="google/gemini-2.5-flash"
        />
        <div className="flex items-center gap-3 mt-4">
          <Button onClick={test} variant="secondary" disabled={testing}>
            {testing ? "接続中…" : "接続テスト"}
          </Button>
          {testResult && <span className="text-sm">{testResult}</span>}
        </div>
      </Card>

      <Card>
        <h2 className="font-semibold mb-2">学習パラメータ</h2>
        <label className={label}>1 日の新規カード上限（デッキ既定）</label>
        <input
          className={field}
          type="number"
          value={s.new_per_day}
          onChange={(e) => update({ new_per_day: e.target.value })}
        />
        <label className={label}>目標保持率（FSRS desired retention, 0〜1）</label>
        <input
          className={field}
          value={s.desired_retention}
          onChange={(e) => update({ desired_retention: e.target.value })}
        />
        <label className={label}>生成時のコンテキスト文字数上限</label>
        <input
          className={field}
          type="number"
          value={s.context_char_budget}
          onChange={(e) => update({ context_char_budget: e.target.value })}
        />
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={save}>保存</Button>
        {saved && <span className="text-sm text-emerald-600">保存しました</span>}
      </div>
    </div>
  );
}
