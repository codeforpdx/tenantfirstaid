import { describe, it } from "vitest";
import { renderWithProviders } from "../testUtils";

const renderLayout = async (path: string) => {
  const { default: Layout } = await import("../../layouts/PageLayout");
  return renderWithProviders(
    <Layout>
      <div />
    </Layout>,
    { route: path },
  );
};

describe("Page Layout component", () => {
  const pageSetup = async (path: string) => {
    const { container } = await renderLayout(path);
    return container.querySelector("#page-layout");
  };

  it("returns lg:h-dvh when path is index", async () => {
    const pageLayout = await pageSetup("/");

    expect(pageLayout).toHaveClass("min-h-dvh", "lg:h-dvh");
    expect(pageLayout).not.toHaveClass("sm:pt-32", "sm:pb-16");
  });

  it("returns lg:h-dvh when path starts with /letter", async () => {
    const pageLayout = await pageSetup("/letter/oregon-law-help");

    expect(pageLayout).toHaveClass("min-h-dvh", "lg:h-dvh");
    expect(pageLayout).not.toHaveClass("sm:pt-32", "sm:pb-16");
  });

  it("returns sm:pt-32 sm:pb-16 when path is not / or starts with /letter", async () => {
    const pageLayout = await pageSetup("/about");

    expect(pageLayout).not.toHaveClass("h-dvh");
    expect(pageLayout).toHaveClass("sm:pt-32", "sm:pb-16");
  });
});
