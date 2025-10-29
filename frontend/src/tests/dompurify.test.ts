import DOMPurify, { SANITIZE_SETTINGS } from "../shared/utils/dompurify";
import { describe, it, expect } from "vitest";

describe("DOMPurify sanitization", () => {
  it("should remove <script>, <style>, <iframe>, <object>, and <embed> tags", () => {
    const dirty = `
      <p>safe</p>
      <script>alert('xss')</script>
      <style>body { background: red; }</style>
      <iframe src="https://evil.com"></iframe>
      <object data="evil.swf"></object>
      <embed src="evil.mp4"></embed>
    `;

    const clean = DOMPurify.sanitize(dirty, SANITIZE_SETTINGS).trim();

    expect(clean).toBe("<p>safe</p>");
  });

  it("should keep allowed tags like <a>, <strong>, <em>, <p>", () => {
    const dirty = `
      <p>Paragraph</p>
      <b>bold</b>
      <em>italic</em>
      <strong>strong</strong>
      <a href="#">link</a>
      <div>div tag</div>
      <span>span tag</span>
      <u>underlined</u>
    `;

    const clean = DOMPurify.sanitize(dirty, SANITIZE_SETTINGS);

    expect(clean).toContain("<p>");
    expect(clean).toContain("<em>");
    expect(clean).toContain("<strong>");
    expect(clean).toContain("<a");

    expect(clean).not.toContain("<div>");
    expect(clean).not.toContain("<b>");
    expect(clean).not.toContain("<span>");
    expect(clean).not.toContain("<u>");
  });

  it("should add rel and target to <a> tags via hook", () => {
    const dirty = `<a href="https://example.com">Example</a>`;

    const clean = DOMPurify.sanitize(dirty, SANITIZE_SETTINGS);

    const link = new DOMParser().parseFromString(clean, "text/html").body
      .firstChild as HTMLAnchorElement;

    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
  });

  it("should strip disallowed attributes", () => {
    const dirty = `<p onclick="alert('xss')">Click me</p>`;

    const clean = DOMPurify.sanitize(dirty, SANITIZE_SETTINGS).trim();

    expect(clean).toBe("<p>Click me</p>");
  });
});
