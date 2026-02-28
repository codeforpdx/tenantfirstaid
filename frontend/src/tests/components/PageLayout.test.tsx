import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { describe, it } from "vitest";
import HousingContextProvider from "../../contexts/HousingContext";
import { MemoryRouter } from "react-router-dom";

beforeAll(() => {
  if (!("scrollTo" in HTMLElement.prototype)) {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    HTMLElement.prototype.scrollTo = function () {};
  }
  HTMLDialogElement.prototype.showModal = vi.fn();
  HTMLDialogElement.prototype.close = vi.fn();
});

const renderLayout = async (path: string) => {
  const { default: Layout } = await import("../../layouts/PageLayout");
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <HousingContextProvider>
        <MemoryRouter initialEntries={[path]}>
          <Layout>
            <div />
          </Layout>
        </MemoryRouter>
      </HousingContextProvider>
    </QueryClientProvider>,
  );
};

describe("Page Layout component", () => {
  const pageSetup = async (path: string) => {
    const { container } = await renderLayout(path);
    return container.querySelector("#page-layout");
  };

  it("returns h-dvh when path is index", async () => {
    const pageLayout = await pageSetup("/");

    expect(pageLayout).toHaveClass("h-dvh");
    expect(pageLayout).not.toHaveClass("sm:pt-32", "sm:pb-16");
  });

  it("returns h-dvh when path starts with /letter", async () => {
    const pageLayout = await pageSetup("/letter/oregon-law-help");

    expect(pageLayout).toHaveClass("h-dvh");
    expect(pageLayout).not.toHaveClass("sm:pt-32", "sm:pb-16");
  });

  it("returns sm:pt-32 sm:pb-16 when path is not / or starts with /letter", async () => {
    const pageLayout = await pageSetup("/about");

    expect(pageLayout).not.toHaveClass("h-dvh");
    expect(pageLayout).toHaveClass("sm:pt-32", "sm:pb-16");
  });
});
