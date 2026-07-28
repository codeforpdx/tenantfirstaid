import clsx from "clsx";
import { useLocation } from "react-router";

interface Props {
  children: React.ReactNode;
}

export default function PageLayout({ children }: Props) {
  const { pathname } = useLocation();
  const isChatOrHomePages =
    pathname === "/" ||
    pathname.startsWith("/letter") ||
    pathname.startsWith("/chat");

  return (
    <div
      className={clsx(
        "flex justify-center pt-(--navbar-height) pb-(--footer-height)",
        isChatOrHomePages
          ? "min-h-dvh lg:h-dvh"
          : "items-center sm:pt-32 sm:pb-16",
      )}
      id="page-layout"
    >
      {children}
    </div>
  );
}
