import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  vi,
  type Mock,
} from "vitest";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import sendFeedback from "../../pages/Chat/utils/feedbackHelper";
import type { ChatMessage, UiMessage } from "../../shared/types/messages";

describe("sendFeedback", () => {
  let fetchSpy: Mock<typeof fetch>;

  beforeEach(() => {
    fetchSpy = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function getTranscriptHtml(): Promise<string> {
    // oxlint-disable-next-line no-unsafe-type-assertion -- sendFeedback always posts a FormData body.
    const formData = fetchSpy.mock.calls[0][1]!.body as FormData;
    const transcript = formData.get("transcript");
    if (!(transcript instanceof Blob)) {
      throw new Error("expected transcript form field to be a Blob");
    }
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.addEventListener("load", (e) => {
        const result = e.target?.result;
        if (typeof result !== "string") {
          throw new Error("expected FileReader result to be a string");
        }
        resolve(result);
      });
      reader.readAsText(transcript);
    });
  }

  it("should not send when messages array has fewer than 2 messages", async () => {
    await sendFeedback([], "feedback", "", "");
    expect(fetchSpy).not.toHaveBeenCalled();

    await sendFeedback(
      [new HumanMessage({ content: "Single", id: "1" })],
      "feedback",
      "",
      "",
    );
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
    // oxlint-disable-next-line no-unsafe-type-assertion -- sendFeedback always posts a FormData body.
    const formData = fetchSpy.mock.calls[0][1]!.body as FormData;
    expect(formData.get("feedback")).toBe("Very helpful!");
    expect(formData.get("emailsToCC")).toBe("cc@example.com");
    expect(formData.get("transcript")).toBeInstanceOf(Blob);
  });

  it("should throw when the server responds with a non-ok status", async () => {
    fetchSpy.mockResolvedValue(new Response(null, { status: 500 }));

    const messages: ChatMessage[] = [
      new HumanMessage({ content: "Hello", id: "1" }),
      new AIMessage({ content: "Hi", id: "2" }),
    ];

    await expect(sendFeedback(messages, "feedback", "", "")).rejects.toThrow(
      "Feedback submission failed with status 500",
    );
  });
});
