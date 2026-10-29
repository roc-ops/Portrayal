// Two element builders every page module uses, bound to the document the view
// is given: dom(doc) returns {el, svgEl, importDrawingNode} that make every
// node through `doc`, so a view never reads `document` as a global.
// The showcase's artifact.js re-exports these: a tool page must not import
// artifact.js, which looks up the showcase's own elements when it loads.
export const dom = doc => {
  const el = (tag, attrs = {}, kids = []) => {
    const n = doc.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') n.className = v;
      else if (k === 'html') n.innerHTML = v;
      else if (k === 'text') n.textContent = v;
      else n.setAttribute(k, v);
    }
    for (const c of [].concat(kids)) n.append(c);
    return n;
  };
  const svgEl = (tag, attrs = {}) => {
    const n = doc.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
  };

  // A compiled drawing's child, imported for the stage WITHOUT its native
  // <title>s: they name parts by drawing id ("port-24--jack"), and a hover on a
  // jack under a cable showed one as a browser tooltip (#186). Null for a
  // title that is itself a child of the drawing.
  const importDrawingNode = kid => {
    if (kid.nodeName === 'title') return null;
    const n = doc.importNode(kid, true);
    if (n.querySelectorAll) for (const t of n.querySelectorAll('title')) t.remove();
    return n;
  };
  return {el, svgEl, importDrawingNode};
};

// A client (screen) point mapped into an <svg>'s own user-space y - shared by
// drag.js (the pointer during a drag) and rack-page.js's onPaneClick (a click
// on a through panel, to find the U under it). (The point class is the svg's
// own window's.)
export const svgY = (svg, clientX, clientY) =>
  new svg.ownerDocument.defaultView.DOMPoint(clientX, clientY).matrixTransform(svg.getScreenCTM().inverse()).y;
