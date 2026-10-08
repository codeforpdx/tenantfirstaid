import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import sendFeedback from "../../pages/Chat/utils/feedbackHelper";
import type { ChatMessage, UiMessage } from "../../shared/types/messages";

describe("sendFeedback", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchSpy);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function getTranscriptHtml(): Promise<string> {
    const formData: FormData = fetchSpy.mock.calls[0][1].body;
    const blob = formData.get("transcript") as Blob;
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.readAsText(blob);
    });
  }

  it("should throw without sending when fewer than 2 non-ui messages exist", async () => {
    await expect(sendFeedback([], "feedback", "", "")).rejects.toThrow();

    const uiMessage: UiMessage = { type: "ui", text: "Error", id: "2" };
    await expect(
      sendFeedback(
        [new HumanMessage({ content: "Single", id: "1" }), uiMessage],
        "feedback",
        "",
        "",
      ),
    ).rejects.toThrow();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("should deserialize JSONL AI message content to plain text", async () => {
    const jsonlContent =
      '{"type":"text","content":"Here is your answer."}\n{"type":"letter","content":"Dear Landlord,\\n\\nPlease fix the heater."}';
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "Write a letter", id: "1" }),
      new AIMessage({ content: jsonlContent, id: "2" }),
    ];

    await sendFeedback(messages, "Great tool!", "", "");

    const html = await getTranscriptHtml();
    expect(html).toContain("Here is your answer.");
    expect(html).toContain("Dear Landlord,");
    expect(html).not.toContain('"type":"text"');
    expect(html).not.toContain('"type":"letter"');
  });

  it("should exclude ui messages from the transcript", async () => {
    const uiMessage: UiMessage = {
      type: "ui",
      text: "Sorry, I encountered an error.",
      id: "3",
    };
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "Hello", id: "1" }),
      new AIMessage({ content: "Hi there", id: "2" }),
      uiMessage,
    ];

    await sendFeedback(messages, "feedback", "", "");

    const html = await getTranscriptHtml();
    expect(html).not.toContain("Sorry, I encountered an error.");
    const paragraphCount = (html.match(/<p>/g) || []).length;
    expect(paragraphCount).toBe(2);
  });

  it("should redact specified words from the transcript", async () => {
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "My name is John Smith", id: "1" }),
      new AIMessage({ content: "Hello John Smith", id: "2" }),
    ];

    await sendFeedback(messages, "feedback", "", "John Smith");

    const html = await getTranscriptHtml();
    expect(html).not.toContain("John Smith");
    expect(html).toContain("background-color: black");
  });

  it("should redact words containing regex or HTML special characters", async () => {
    const messages: ChatMessage[] = [
      new HumanMessage({
        content: "Call (503) 555-1234 for Tom's unit",
        id: "1",
      }),
      new AIMessage({ content: "Noted.", id: "2" }),
    ];

    await sendFeedback(messages, "feedback", "", "(503) 555-1234, Tom's");

    const html = await getTranscriptHtml();
    expect(html).not.toContain("555-1234");
    expect(html).not.toContain("Tom&#039;s");
  });

  it("should still send when a redaction term is an invalid regex", async () => {
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "I code in C++ at (503", id: "1" }),
      new AIMessage({ content: "Noted.", id: "2" }),
    ];

    await sendFeedback(messages, "feedback", "", "C++, (503");

    const html = await getTranscriptHtml();
    expect(html).not.toContain("C++");
    expect(html).not.toContain("(503");
  });

  it("should strip anchor tags around a redacted term", async () => {
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "Hi", id: "1" }),
      new AIMessage({
        content: '<a href="https://example.com/john">John</a> called',
        id: "2",
      }),
    ];

    await sendFeedback(messages, "feedback", "", "John");

    const html = await getTranscriptHtml();
    expect(html).not.toContain("href");
    expect(html).not.toContain("john");
    expect(html).toContain("background-color: black");
  });

  it("should not corrupt HTML entities when a term matches entity text", async () => {
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "rent & deposit for Tom's unit", id: "1" }),
      new AIMessage({ content: "Noted.", id: "2" }),
    ];

    await sendFeedback(messages, "feedback", "", "amp, 039");

    const html = await getTranscriptHtml();
    expect(html).toContain("rent &amp; deposit for Tom&#039;s unit");
    expect(html).not.toContain("background-color: black");
  });

  it("should not match a later term inside an earlier redaction", async () => {
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "Tom is here", id: "1" }),
      new AIMessage({ content: "Noted.", id: "2" }),
    ];

    await sendFeedback(messages, "feedback", "", "Tom, black");

    const html = await getTranscriptHtml();
    expect(html.match(/<span/g)).toHaveLength(1);
    expect(html).toContain("</span> is here");
  });

  it("should treat accented letters as part of a word", async () => {
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "José and Nguyễn", id: "1" }),
      new AIMessage({ content: "Noted.", id: "2" }),
    ];

    await sendFeedback(messages, "feedback", "", "Jos, Nguyễn");

    const html = await getTranscriptHtml();
    expect(html).toContain("José");
    expect(html).not.toContain("Nguyễn");
  });

  it("should throw when the server responds with an error", async () => {
    fetchSpy.mockResolvedValue({ ok: false, status: 500 });
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "Hello", id: "1" }),
      new AIMessage({ content: "Hi", id: "2" }),
    ];

    await expect(sendFeedback(messages, "feedback", "", "")).rejects.toThrow(
      "500",
    );
  });

  it("should post to /api/feedback with correct form fields", async () => {
    const messages: ChatMessage[] = [
      new HumanMessage({ content: "Hello", id: "1" }),
      new AIMessage({ content: "Hi", id: "2" }),
    ];

    await sendFeedback(messages, "Very helpful!", "cc@example.com", "");

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/feedback",
      expect.objectContaining({ method: "POST" }),
    );
    const formData: FormData = fetchSpy.mock.calls[0][1].body;
    expect(formData.get("feedback")).toBe("Very helpful!");
    expect(formData.get("emailsToCC")).toBe("cc@example.com");
    expect(formData.get("transcript")).toBeInstanceOf(Blob);
  });
});
