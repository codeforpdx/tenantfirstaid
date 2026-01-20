export default function sanitizeText(str: string) {
  // Strips anchor tags
  str = str.replace(/<a\b[^>]*>(.*?)<\/a>/gi, "$1");

  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
