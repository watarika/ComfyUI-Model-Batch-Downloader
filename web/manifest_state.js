export const MODEL_TYPES = [
  "checkpoints",
  "diffusion_models",
  "text_encoders",
  "vae",
  "loras",
  "controlnet",
  "embeddings",
  "upscale_models",
  "onnx",
  "sam3",
  "llm",
  "ultralytics_bbox",
  "ultralytics_segm",
];

export function emptyRow() {
  return {
    url: "",
    model_type: "checkpoints",
    subfolder: "",
    filename: "",
    id: "",
    split: 16,
  };
}

export function parseRows(value) {
  try {
    const parsed = JSON.parse(value || "[]");
    if (!Array.isArray(parsed) || parsed.length === 0) return [emptyRow()];
    return parsed.map((item) => ({ ...emptyRow(), ...item }));
  } catch {
    return [emptyRow()];
  }
}

export function serializeRows(rows) {
  return JSON.stringify(
    rows.map((row) => {
      const item = {
        url: String(row.url ?? "").trim(),
        model_type: row.model_type,
        split: Math.min(16, Math.max(1, Number.parseInt(row.split, 10) || 16)),
      };
      for (const key of ["subfolder", "filename", "id"]) {
        const value = String(row[key] ?? "").trim();
        if (value) item[key] = value;
      }
      return item;
    }),
    null,
    2,
  );
}

export const addRow = (rows) => [...rows, emptyRow()];
export const removeRow = (rows, index) =>
  rows.filter((_row, current) => current !== index);
