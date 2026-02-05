import sanitizeText from "../../shared/utils/sanitizeText";

describe("sanitizeText", () => {
  it("should escape all HTML special characters", () => {
    expect(sanitizeText("A & B < C > D \"E\" 'F'")).toBe(
      "A &amp; B &lt; C &gt; D &quot;E&quot; &#039;F&#039;",
    );
  });

  it("should strip anchor tags with various attributes and formats", () => {
    expect(
      sanitizeText(
        '<a href="one.com">First</a> and <A HREF="two.com" target="_blank">Second</A>',
      ),
    ).toBe("First and Second");
  });

  it("should strip anchor tags but escape nested HTML", () => {
    expect(sanitizeText('<a href="test.com">Click <em>here</em></a>')).toBe(
      "Click &lt;em&gt;here&lt;/em&gt;",
    );
  });

  it("should escape dangerous HTML tags and attributes", () => {
    expect(
      sanitizeText(
        '<script>alert("xss")</script><img src=x onerror="alert(1)">',
      ),
    ).toBe(
      "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
    );
  });

  it("should handle mixed anchor tags and malicious scripts", () => {
    expect(sanitizeText('<a href="x">link</a><script>alert(1)</script>')).toBe(
      "link&lt;script&gt;alert(1)&lt;/script&gt;",
    );
  });

  it("should handle empty strings and strings without special characters", () => {
    expect(sanitizeText("")).toBe("");
    expect(sanitizeText("Hello World")).toBe("Hello World");
  });

  it("should handle malformed anchor tags", () => {
    expect(sanitizeText('<a href="test.com">Unclosed tag')).toBe(
      "&lt;a href=&quot;test.com&quot;&gt;Unclosed tag",
    );
  });

  it("should handle edge case character patterns", () => {
    expect(sanitizeText("&&& Hello 世界 🌍")).toBe(
      "&amp;&amp;&amp; Hello 世界 🌍",
    );
  });

  it("should strip anchors before escaping HTML", () => {
    expect(sanitizeText('<a href="test.com"><b>Bold & text</b></a>')).toBe(
      "&lt;b&gt;Bold &amp; text&lt;/b&gt;",
    );
  });
});
