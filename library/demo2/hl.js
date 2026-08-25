// Shared highlight helper: the drop-shadow glow alone gets painted over by
// neighbors drawn later (touching cages lose the shared edge), so highlights
// also add a crisp outline rect appended last in the SVG — always on top.
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  function rootRect(el) {
    const svg = el.ownerSVGElement;
    const b = el.getBBox();
    const m = svg.getScreenCTM().inverse().multiply(el.getScreenCTM());
    const pts = [[b.x, b.y], [b.x + b.width, b.y], [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]]
      .map(([x, y]) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f}));
    const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
    return {x: Math.min(...xs), y: Math.min(...ys),
            w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)};
  }
  window.portrayalHl = {
    on(el) {
      if (!el) return;
      el.classList.add('portrayal-highlight');
      const svg = el.ownerSVGElement;
      if (!svg || el.__hlRect) return;
      const r = rootRect(el);
      const rect = document.createElementNS(NS, 'rect');
      rect.setAttribute('class', 'portrayal-hl-rect');
      rect.setAttribute('x', r.x - 0.45); rect.setAttribute('y', r.y - 0.45);
      rect.setAttribute('width', r.w + 0.9); rect.setAttribute('height', r.h + 0.9);
      rect.setAttribute('rx', 0.7);
      rect.setAttribute('fill', 'none');
      rect.setAttribute('stroke', '#f59e0b');
      rect.setAttribute('stroke-width', 0.7);
      rect.setAttribute('pointer-events', 'none');
      svg.appendChild(rect);
      el.__hlRect = rect;
    },
    off(el) {
      if (!el) return;
      el.classList.remove('portrayal-highlight');
      if (el.__hlRect) { el.__hlRect.remove(); el.__hlRect = null; }
    },
    clear() {
      document.querySelectorAll('.portrayal-hl-rect').forEach(x => x.remove());
      document.querySelectorAll('.portrayal-highlight').forEach(e => {
        e.classList.remove('portrayal-highlight');
        e.__hlRect = null;
      });
    }
  };
})();
