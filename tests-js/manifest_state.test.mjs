import test from "node:test";
import assert from "node:assert/strict";
import {
  MODEL_TYPES,
  addRow,
  emptyRow,
  parseRows,
  removeRow,
  serializeRows,
} from "../web/manifest_state.js";

test("model types include every supported download category", () => {
  assert.deepEqual(MODEL_TYPES, [
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
  ]);
});

test("empty row has canonical defaults", () => {
  assert.deepEqual(emptyRow(), {
    url: "",
    model_type: "checkpoints",
    subfolder: "",
    filename: "",
    id: "",
    split: 16,
  });
});

test("serialization omits optional empty fields", () => {
  const json = serializeRows([
    { ...emptyRow(), url: "https://example.com/a.safetensors" },
  ]);
  assert.deepEqual(JSON.parse(json), [
    {
      url: "https://example.com/a.safetensors",
      model_type: "checkpoints",
      split: 16,
    },
  ]);
});

test("add and remove are immutable", () => {
  const original = [emptyRow()];
  const added = addRow(original);
  const removed = removeRow(added, 0);
  assert.equal(original.length, 1);
  assert.equal(added.length, 2);
  assert.equal(removed.length, 1);
});

test("invalid stored JSON recovers to one row", () => {
  assert.deepEqual(parseRows("not json"), [emptyRow()]);
});
