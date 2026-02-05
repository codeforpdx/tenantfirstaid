import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import exportMessages from "../../pages/Chat/utils/exportHelper";
import { IMessage } from "../../hooks/useMessages";

function createMockDocument() {
  const writelnCalls: string[] = [];

  return {
    writeln: vi.fn((content: string) => {
      writelnCalls.push(content);
    }),
    writelnCalls,
    close: vi.fn(),
    focus: vi.fn(),
    print: vi.fn(),
    document: {
      writeln: vi.fn((content: string) => {
        writelnCalls.push(content);
      }),
      close: vi.fn(),
    },
  };
}

describe("exportMessages", () => {
  let mockDocument: ReturnType<typeof createMockDocument>;
  let windowOpenSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockDocument = createMockDocument();
    windowOpenSpy = vi.fn(() => mockDocument);
    vi.stubGlobal("window", { open: windowOpenSpy });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("should not export when messages array has fewer than 2 messages", () => {
    exportMessages([]);
    expect(windowOpenSpy).not.toHaveBeenCalled();

    exportMessages([
      { role: "user", content: "Single message", messageId: "1" },
    ]);
    expect(windowOpenSpy).not.toHaveBeenCalled();
  });

  it("should open window, generate HTML with sanitized content, and trigger print", () => {
    const messages: IMessage[] = [
      {
        role: "user",
        content: '<script>alert("xss")</script>',
        messageId: "1",
      },
      { role: "ai", content: "Safe & <secure>", messageId: "2" },
      { role: "user", content: "Third message", messageId: "3" },
    ];

    exportMessages(messages);

    // Window creation
    expect(windowOpenSpy).toHaveBeenCalledWith("", "", "height=800,width=600");

    const html = mockDocument.writelnCalls.join("");

    // HTML structure and security
    expect(html).toContain("<title>Conversation History</title>");
    expect(html).toContain("Content-Security-Policy");
    expect(html).toContain("script-src 'none'");
    expect(html).toContain("font-family: sans-serif");

    // Role capitalization and all messages included
    expect(html).toContain("<strong>User</strong>");
    expect(html).toContain("<strong>AI</strong>");
    const paragraphCount = (html.match(/<p>/g) || []).length;
    expect(paragraphCount).toBe(3);

    // Content sanitization
    expect(html).toContain("&lt;script&gt;");
    expect(html).toContain("&amp;");
    expect(html).not.toContain("<script>alert");

    // Document operations
    expect(mockDocument.document.writeln).toHaveBeenCalledTimes(1);
    expect(mockDocument.document.close).toHaveBeenCalledTimes(1);
    expect(mockDocument.focus).toHaveBeenCalledTimes(1);
    expect(mockDocument.print).toHaveBeenCalledTimes(1);
  });

  it("should handle edge cases gracefully", () => {
    // Null window (popup blocker)
    vi.stubGlobal("window", { open: vi.fn(() => null) });
    expect(() =>
      exportMessages([
        { role: "user", content: "Test", messageId: "1" },
        { role: "ai", content: "Response", messageId: "2" },
      ]),
    ).not.toThrow();

    // Empty content and special characters
    vi.stubGlobal("window", { open: vi.fn(() => mockDocument) });
    exportMessages([
      { role: "user", content: "", messageId: "1" },
      {
        role: "ai",
        content: '<a href="link.com">Click</a> & "quoted"',
        messageId: "2",
      },
    ]);

    const html = mockDocument.writelnCalls.join("");
    expect(html).toContain("Click &amp; &quot;quoted&quot;");
    expect(html).not.toContain("<a href");
  });
});
