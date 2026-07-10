import test from "node:test";
import assert from "node:assert/strict";

import {
  editorHeight,
  editorLayout,
  hideWidget,
} from "../web/widget_layout.js";

test("hidden manifest widget is removed from DOM and layout", () => {
  const widget = {
    type: "customtext",
    hidden: false,
    computeSize: () => [400, 200],
    element: { style: { display: "", visibility: "" } },
  };

  hideWidget(widget);

  assert.equal(widget.type, "hidden");
  assert.equal(widget.hidden, true);
  assert.equal(widget.computeSize, undefined);
  assert.equal(widget.element.style.display, "none");
  assert.equal(widget.element.style.visibility, "hidden");
  assert.deepEqual(widget.computeLayoutSize(), {
    minHeight: 0,
    maxHeight: 0,
    minWidth: 0,
  });
});

test("editor height grows by row and stops at a scrollable maximum", () => {
  assert.equal(editorHeight(1), 254);
  assert.equal(editorHeight(2), 464);
  assert.equal(editorHeight(20), 620);
  assert.deepEqual(editorLayout(2), {
    minHeight: 464,
    maxHeight: 464,
    minWidth: 480,
  });
});
