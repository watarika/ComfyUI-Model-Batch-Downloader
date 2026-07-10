export function hideWidget(widget) {
  widget.type = "hidden";
  widget.hidden = true;
  widget.computeSize = undefined;
  widget.computeLayoutSize = () => ({
    minHeight: 0,
    maxHeight: 0,
    minWidth: 0,
  });
  if (widget.element) {
    widget.element.style.display = "none";
    widget.element.style.visibility = "hidden";
  }
}

export function editorHeight(rowCount) {
  return Math.min(620, 44 + Math.max(1, rowCount) * 210);
}

export function editorLayout(rowCount) {
  const height = editorHeight(rowCount);
  return {
    minHeight: height,
    maxHeight: height,
    minWidth: 480,
  };
}
