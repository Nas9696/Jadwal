"use client";

import { useEffect } from "react";

const arabicDigits = "٠١٢٣٤٥٦٧٨٩";

function localizeText(node: Text) {
  const parent = node.parentElement;
  if (!parent || parent.closest("script, style, code, pre, input, textarea")) return;
  const next = node.data.replace(/\d/g, (digit) => arabicDigits[Number(digit)]);
  if (next !== node.data) node.data = next;
}

function localizeTree(root: Node) {
  if (root.nodeType === Node.TEXT_NODE) return localizeText(root as Text);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    localizeText(node as Text);
    node = walker.nextNode();
  }
}

export function ArabicDigits() {
  useEffect(() => {
    localizeTree(document.body);
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData") localizeText(mutation.target as Text);
        for (const node of mutation.addedNodes) localizeTree(node);
      }
    });
    observer.observe(document.body, { childList: true, characterData: true, subtree: true });
    return () => observer.disconnect();
  }, []);
  return null;
}
