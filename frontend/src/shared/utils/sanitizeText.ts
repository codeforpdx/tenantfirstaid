/**
 * Strips all <a> tags while preserving their inner text content.
 */
export function stripAnchorTags(str: string) {
  return str.replace(/<a\b[^>]*>(.*?)<\/a>/gi, "$1");
}

/**
 * Escapes HTML special characters to prevent XSS attacks and rendering issues.
 */
export function escapeHtml(str: string) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

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
  return escapeHtml(stripAnchorTags(str));
}
