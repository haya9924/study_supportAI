import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Course, Material } from "../api";
import { Button, Card, Empty } from "../components/ui";

export default function Materials() {
  const nav = useNavigate();
  const [courses, setCourses] = useState<Course[]>([]);
  const [uncategorized, setUncategorized] = useState(0);
  const [newCourse, setNewCourse] = useState("");
  const [renaming, setRenaming] = useState<number | null>(null);
  const [renameVal, setRenameVal] = useState("");

  const load = () => {
    api.get<Course[]>("/api/courses").then(setCourses);
    api
      .get<Material[]>("/api/materials?uncategorized=1")
      .then((m) => setUncategorized(m.length));
  };
  useEffect(() => {
    load();
  }, []);

  const addCourse = async () => {
    if (!newCourse.trim()) return;
    await api.post("/api/courses", { name: newCourse });
    setNewCourse("");
    load();
  };

  const saveRename = async (id: number) => {
    if (renameVal.trim()) await api.put(`/api/courses/${id}`, { name: renameVal });
    setRenaming(null);
    load();
  };

  const removeCourse = async (id: number) => {
    if (!confirm("この科目フォルダと中の教材をすべて削除しますか？")) return;
    await api.del(`/api/courses/${id}`);
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">教材</h1>
      </div>

      <Card>
        <label className="block text-sm font-medium mb-1">
          新しい科目フォルダを作成
        </label>
        <div className="flex gap-2">
          <input
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="例: 生物学、線形代数…"
            value={newCourse}
            onChange={(e) => setNewCourse(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCourse()}
          />
          <Button onClick={addCourse}>作成</Button>
        </div>
      </Card>

      <div>
        <div className="text-sm text-slate-500 mb-2">
          フォルダを開いて教材をアップロード・管理します
        </div>
        {courses.length === 0 && uncategorized === 0 ? (
          <Empty>
            まだフォルダがありません。科目を作成して教材を追加しましょう。
          </Empty>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {courses.map((c) => (
              <div
                key={c.id}
                className="group bg-white border border-slate-200 rounded-xl p-4 hover:border-indigo-300 hover:shadow-sm transition cursor-pointer"
                onClick={() =>
                  renaming !== c.id && nav(`/materials/course/${c.id}`)
                }
              >
                <div className="flex items-start justify-between">
                  <div className="text-3xl">📁</div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                    <button
                      title="名前を変更"
                      className="text-slate-400 hover:text-slate-700 text-sm px-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        setRenaming(c.id);
                        setRenameVal(c.name);
                      }}
                    >
                      ✏️
                    </button>
                    <button
                      title="削除"
                      className="text-slate-400 hover:text-red-600 text-sm px-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeCourse(c.id);
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
                {renaming === c.id ? (
                  <input
                    autoFocus
                    className="mt-2 w-full border border-slate-300 rounded px-2 py-1 text-sm"
                    value={renameVal}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => setRenameVal(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") saveRename(c.id);
                      if (e.key === "Escape") setRenaming(null);
                    }}
                    onBlur={() => saveRename(c.id)}
                  />
                ) : (
                  <div className="mt-2 font-medium truncate">{c.name}</div>
                )}
                <div className="text-xs text-slate-400 mt-0.5">
                  {c.material_count} 件
                </div>
              </div>
            ))}

            {/* 未分類フォルダ */}
            <div
              className="bg-white border border-slate-200 border-dashed rounded-xl p-4 hover:border-indigo-300 hover:shadow-sm transition cursor-pointer"
              onClick={() => nav("/materials/course/none")}
            >
              <div className="text-3xl">🗂️</div>
              <div className="mt-2 font-medium truncate text-slate-600">
                未分類
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                {uncategorized} 件
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
