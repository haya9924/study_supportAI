import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, Course, Material } from "../api";
import { Badge, Button, Card, Empty, Spinner } from "../components/ui";

const KIND_LABEL: Record<string, string> = {
  lecture: "講義資料",
  past_exam: "過去問",
  other: "その他",
};

export default function Materials() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseId, setCourseId] = useState<number | null>(null);
  const [kind, setKind] = useState("lecture");
  const [newCourse, setNewCourse] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = () => {
    api.get<Material[]>("/api/materials").then(setMaterials);
    api.get<Course[]>("/api/courses").then(setCourses);
  };
  useEffect(() => {
    load();
  }, []);

  // 処理中の教材があれば定期更新
  useEffect(() => {
    if (!materials.some((m) => m.status === "processing")) return;
    const t = setInterval(
      () => api.get<Material[]>("/api/materials").then(setMaterials),
      2500
    );
    return () => clearInterval(t);
  }, [materials]);

  const addCourse = async () => {
    if (!newCourse.trim()) return;
    const c = await api.post<Course>("/api/courses", { name: newCourse });
    setNewCourse("");
    setCourseId(c.id);
    load();
  };

  const upload = async (files: FileList) => {
    if (files.length === 0) return;
    setUploading(true);
    const form = new FormData();
    for (const f of Array.from(files)) form.append("files", f);
    if (courseId != null) form.append("course_id", String(courseId));
    form.append("kind", kind);
    try {
      await api.upload("/api/materials", form);
      load();
    } catch (e) {
      alert("アップロード失敗: " + (e as Error).message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const remove = async (id: number) => {
    if (!confirm("この教材を削除しますか？")) return;
    await api.del(`/api/materials/${id}`);
    load();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">教材</h1>

      <Card>
        <h2 className="font-semibold mb-3">アップロード</h2>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-sm font-medium mb-1">科目</label>
            <div className="flex gap-2">
              <select
                className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm"
                value={courseId ?? ""}
                onChange={(e) =>
                  setCourseId(e.target.value ? Number(e.target.value) : null)
                }
              >
                <option value="">未分類</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-2 mt-2">
              <input
                className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                placeholder="新しい科目名"
                value={newCourse}
                onChange={(e) => setNewCourse(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addCourse()}
              />
              <Button variant="secondary" onClick={addCourse}>
                追加
              </Button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">種別</label>
            <select
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              <option value="lecture">講義資料・スライド</option>
              <option value="past_exam">過去問</option>
              <option value="other">その他</option>
            </select>
          </div>
        </div>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.heic,.heif,.webp"
          onChange={(e) => e.target.files && upload(e.target.files)}
          className="block w-full text-sm"
          disabled={uploading}
        />
        <p className="text-xs text-slate-400 mt-2">
          PDF / JPEG / PNG / HEIC 対応。アップロード後、自動で OCR を実行します。
        </p>
        {uploading && (
          <div className="flex items-center gap-2 mt-2 text-sm text-slate-500">
            <Spinner /> アップロード中…
          </div>
        )}
      </Card>

      <div>
        <h2 className="font-semibold mb-2">教材一覧</h2>
        {materials.length === 0 ? (
          <Empty>まだ教材がありません</Empty>
        ) : (
          <div className="space-y-2">
            {materials.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-4 py-3"
              >
                <Link
                  to={`/materials/${m.id}`}
                  className="flex-1 min-w-0 hover:text-indigo-600"
                >
                  <div className="truncate font-medium">{m.title}</div>
                  <div className="text-xs text-slate-400">
                    {KIND_LABEL[m.kind] || m.kind}
                  </div>
                </Link>
                <div className="flex items-center gap-3">
                  <Badge status={m.status} />
                  <Button variant="ghost" onClick={() => remove(m.id)}>
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
