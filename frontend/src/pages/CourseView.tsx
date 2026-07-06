import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Course, Material } from "../api";
import { Badge, Button, Card, Empty, Spinner } from "../components/ui";

const KIND_LABEL: Record<string, string> = {
  lecture: "講義資料",
  past_exam: "過去問",
  other: "その他",
};

export default function CourseView() {
  const { cid } = useParams();
  const isUncategorized = cid === "none";
  const courseId = isUncategorized ? null : Number(cid);

  const [courses, setCourses] = useState<Course[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [kind, setKind] = useState("lecture");
  const [picked, setPicked] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const courseName = isUncategorized
    ? "未分類"
    : courses.find((c) => c.id === courseId)?.name ?? "…";

  const loadMaterials = useCallback(() => {
    const q = isUncategorized
      ? "?uncategorized=1"
      : `?course_id=${courseId}`;
    api.get<Material[]>("/api/materials" + q).then(setMaterials);
  }, [isUncategorized, courseId]);

  useEffect(() => {
    api.get<Course[]>("/api/courses").then(setCourses);
    loadMaterials();
  }, [loadMaterials]);

  // 処理中があれば定期更新
  useEffect(() => {
    if (!materials.some((m) => m.status === "processing")) return;
    const t = setInterval(loadMaterials, 2500);
    return () => clearInterval(t);
  }, [materials, loadMaterials]);

  const addFiles = (files: FileList | File[]) => {
    setPicked((prev) => [...prev, ...Array.from(files)]);
  };

  const removePicked = (i: number) =>
    setPicked((prev) => prev.filter((_, idx) => idx !== i));

  const doUpload = async () => {
    if (picked.length === 0) return;
    setUploading(true);
    const form = new FormData();
    for (const f of picked) form.append("files", f);
    if (courseId != null) form.append("course_id", String(courseId));
    form.append("kind", kind);
    try {
      await api.upload("/api/materials", form);
      setPicked([]);
      if (fileRef.current) fileRef.current.value = "";
      loadMaterials();
    } catch (e) {
      alert("アップロード失敗: " + (e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const move = async (id: number, target: string) => {
    const course_id = target === "none" ? null : Number(target);
    await api.put(`/api/materials/${id}/move`, { course_id });
    loadMaterials();
    api.get<Course[]>("/api/courses").then(setCourses);
  };

  const remove = async (id: number) => {
    if (!confirm("この教材を削除しますか？")) return;
    await api.del(`/api/materials/${id}`);
    loadMaterials();
  };

  return (
    <div className="space-y-6">
      {/* パンくず */}
      <div className="flex items-center gap-2 text-sm">
        <Link to="/materials" className="text-indigo-600">
          教材
        </Link>
        <span className="text-slate-400">/</span>
        <span className="font-medium">📁 {courseName}</span>
      </div>

      {/* アップロード */}
      <Card>
        <h2 className="font-semibold mb-3">
          このフォルダに教材をアップロード
        </h2>
        <div className="mb-3">
          <label className="block text-sm font-medium mb-1">種別</label>
          <select
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            <option value="lecture">講義資料・スライド</option>
            <option value="past_exam">過去問</option>
            <option value="other">その他</option>
          </select>
        </div>

        {/* ドロップゾーン */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
          }}
          className={`border-2 border-dashed rounded-xl p-6 text-center transition ${
            dragOver
              ? "border-indigo-400 bg-indigo-50"
              : "border-slate-300 bg-slate-50"
          }`}
        >
          <div className="text-slate-500 text-sm mb-3">
            ここにファイルをドラッグ＆ドロップ、または
          </div>
          <input
            ref={fileRef}
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.heic,.heif,.webp"
            onChange={(e) => e.target.files && addFiles(e.target.files)}
            className="hidden"
          />
          <Button variant="secondary" onClick={() => fileRef.current?.click()}>
            ファイルを選択
          </Button>
          <div className="text-xs text-slate-400 mt-2">
            PDF / JPEG / PNG / HEIC 対応
          </div>
        </div>

        {/* 選択中ファイル一覧 */}
        {picked.length > 0 && (
          <div className="mt-4 space-y-2">
            <div className="text-sm font-medium">
              選択中のファイル（{picked.length}）
            </div>
            {picked.map((f, i) => (
              <div
                key={i}
                className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm"
              >
                <span className="truncate">📄 {f.name}</span>
                <button
                  className="text-slate-400 hover:text-red-600 px-1"
                  onClick={() => removePicked(i)}
                  disabled={uploading}
                >
                  ✕
                </button>
              </div>
            ))}
            <div className="flex items-center gap-3 pt-1">
              <Button onClick={doUpload} disabled={uploading}>
                {uploading
                  ? "アップロード中…"
                  : `${picked.length} 件をアップロードする`}
              </Button>
              {uploading && <Spinner />}
            </div>
          </div>
        )}
      </Card>

      {/* 教材一覧 */}
      <div>
        <h2 className="font-semibold mb-2">教材一覧</h2>
        {materials.length === 0 ? (
          <Empty>このフォルダにはまだ教材がありません</Empty>
        ) : (
          <div className="space-y-2">
            {materials.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-4 py-3"
              >
                <Link
                  to={`/materials/${m.id}`}
                  className="flex-1 min-w-0 flex items-center gap-2 hover:text-indigo-600"
                >
                  <span>📄</span>
                  <span className="min-w-0">
                    <span className="block truncate font-medium">
                      {m.title}
                    </span>
                    <span className="block text-xs text-slate-400">
                      {KIND_LABEL[m.kind] || m.kind}
                    </span>
                  </span>
                </Link>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <Badge status={m.status} />
                  <select
                    title="別の科目へ移動"
                    className="border border-slate-200 rounded px-1.5 py-1 text-xs text-slate-500 max-w-28"
                    value={m.course_id ?? "none"}
                    onChange={(e) => move(m.id, e.target.value)}
                  >
                    <option value="none">未分類</option>
                    {courses.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <button
                    className="text-slate-400 hover:text-red-600 text-sm px-1"
                    onClick={() => remove(m.id)}
                  >
                    削除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
