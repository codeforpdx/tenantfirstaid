import DOMPurify from "dompurify";

// Hook runs after every sanitize call
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A") {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  }
});

export const SANITIZE_SETTINGS = {
  ALLOWED_TAGS: ["a", "em", "strong", "p"],
  ALLOWED_ATTR: ["href", "title", "target", "rel"],
  FORBID_TAGS: ["style", "script", "iframe", "object", "embed"],
};

export default DOMPurify;
