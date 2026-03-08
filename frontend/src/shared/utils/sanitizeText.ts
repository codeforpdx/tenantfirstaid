/**
 * Sanitizes a string by removing anchor tags and escaping HTML special characters
 *
 * This function will:
 * 1. Strips all <a> tags while preserving their inner text content
 * 2. Escapes HTML special characters to prevent XSS attacks and rendering issues
 *
 * @returns The sanitized string with anchor tags removed and HTML characters escaped
 */
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
