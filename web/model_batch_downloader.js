import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import {
  MODEL_TYPES,
  addRow,
  parseRows,
  removeRow,
  serializeRows,
} from "./manifest_state.js";
import { editorHeight, hideWidget } from "./widget_layout.js";

const FIELD_LABELS = {
  url: "URL",
  model_type: "Model type",
  subfolder: "Subfolder (optional)",
  filename: "Filename (optional)",
  id: "ID (optional)",
  split: "Connections",
};

function field(row, key, onChange, type = "text") {
  const label = document.createElement("label");
  label.style.cssText = "display:flex;flex-direction:column;gap:2px;font-size:11px";
  label.append(FIELD_LABELS[key]);

  const input = document.createElement(type === "select" ? "select" : "input");
  input.dataset.field = key;
  input.style.cssText = "min-width:0;padding:4px;background:#222;color:#ddd;border:1px solid #666";
  if (type === "select") {
    for (const optionValue of MODEL_TYPES) {
      const option = document.createElement("option");
      option.value = option.textContent = optionValue;
      input.append(option);
    }
  } else {
    input.type = type;
    if (type === "number") {
      input.min = "1";
      input.max = "16";
    }
  }
  input.value = row[key];
  input.addEventListener("change", () => onChange(key, input.value));
  label.append(input);
  return label;
}

function showError(error) {
  app.extensionManager.toast.add({
    severity: "error",
    summary: "Filename resolution failed",
    detail: error instanceof Error ? error.message : String(error),
  });
}

function mountEditor(node, manifestWidget) {
  let rows = parseRows(manifestWidget.value);
  const root = document.createElement("div");
  root.className = "model-batch-downloader-table";
  root.style.cssText =
    "width:100%;height:100%;box-sizing:border-box;padding:4px;overflow:auto";
  let editorWidget;

  const sync = () => {
    manifestWidget.value = serializeRows(rows);
  };

  const render = () => {
    root.replaceChildren();
    rows.forEach((row, index) => {
      const card = document.createElement("div");
      card.style.cssText =
        "display:grid;grid-template-columns:2fr 1fr;gap:6px;padding:8px;" +
        "border:1px solid #666;border-radius:4px;margin:6px 0";
      const update = (key, value) => {
        rows[index] = { ...rows[index], [key]: value };
        sync();
      };

      for (const [key, type] of [
        ["url", "text"],
        ["model_type", "select"],
        ["subfolder", "text"],
        ["filename", "text"],
        ["id", "text"],
        ["split", "number"],
      ]) {
        card.append(field(rows[index], key, update, type));
      }

      const preview = document.createElement("button");
      preview.textContent = "Resolve filename / ID";
      preview.onclick = async () => {
        try {
          const response = await api.fetchApi("/model-batch-downloader/resolve", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: rows[index].url }),
          });
          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.error || "Filename resolution failed");
          }
          rows[index] = {
            ...rows[index],
            filename: data.filename,
            id: data.id,
          };
          sync();
          render();
        } catch (error) {
          showError(error);
        }
      };
      card.append(preview);

      const remove = document.createElement("button");
      remove.textContent = "Remove";
      remove.onclick = () => {
        rows = removeRow(rows, index);
        if (!rows.length) rows = addRow([]);
        sync();
        render();
      };
      card.append(remove);
      root.append(card);
    });

    const add = document.createElement("button");
    add.textContent = "+ Add file";
    add.onclick = () => {
      rows = addRow(rows);
      sync();
      render();
    };
    root.append(add);
    if (editorWidget) {
      const size = node.computeSize();
      node.setSize([Math.max(size[0], 520), size[1]]);
      node.graph?.setDirtyCanvas(true, true);
    }
  };

  hideWidget(manifestWidget);
  editorWidget = node.addDOMWidget(
    "downloads",
    "model-batch-downloader-table",
    root,
    {
      getMinHeight: () => editorHeight(rows.length),
      getMaxHeight: () => editorHeight(rows.length),
      margin: 4,
    },
  );
  editorWidget.serialize = false;
  sync();
  render();
}

app.registerExtension({
  name: "ComfyUI.ModelBatchDownloader.Table",
  nodeCreated(node) {
    if (
      node.comfyClass !== "ModelBatchDownloader" ||
      node.__modelDownloaderMounted
    ) {
      return;
    }
    const manifestWidget = node.widgets?.find(
      (widget) => widget.name === "manifest_json",
    );
    if (!manifestWidget) return;
    node.__modelDownloaderMounted = true;
    mountEditor(node, manifestWidget);
  },
});
