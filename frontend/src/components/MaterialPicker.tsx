import { useEffect, useState } from "react";
import { api, Course, Material } from "../api";

export interface Selection {
  courseId: number | null;
  materialIds: number[];
}

export function MaterialPicker({
  value,
  onChange,
}: {
  value: Selection;
  onChange: (s: Selection) => void;
}) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);

  useEffect(() => {
    api.get<Course[]>("/api/courses").then(setCourses);
  }, []);

  useEffect(() => {
    const q =
      value.courseId != null ? `?course_id=${value.courseId}` : "";
    api.get<Material[]>("/api/materials" + q).then(setMaterials);
  }, [value.courseId]);

  const toggle = (id: number) => {
    const set = new Set(value.materialIds);
    if (set.has(id)) set.delete(id);
    else set.add(id);
    onChange({ ...value, materialIds: [...set] });
  };

  const ready = materials.filter((m) => m.status === "ready");

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium mb-1">科目</label>
        <select
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
          value={value.courseId ?? ""}
          onChange={(e) =>
            onChange({
              courseId: e.target.value ? Number(e.target.value) : null,
              materialIds: [],
            })
          }
        >
          <option value="">すべての科目</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">
          教材を選択（未選択なら科目内すべて）
        </label>
        <div className="max-h-52 overflow-y-auto border border-slate-200 rounded-lg divide-y dark:border-slate-700 dark:divide-slate-700">
          {ready.length === 0 && (
            <div className="text-slate-400 text-sm px-3 py-4">
              文字起こし完了済みの教材がありません
            </div>
          )}
          {ready.map((m) => (
            <label
              key={m.id}
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              <input
                type="checkbox"
                checked={value.materialIds.includes(m.id)}
                onChange={() => toggle(m.id)}
              />
              <span className="truncate">{m.title}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
