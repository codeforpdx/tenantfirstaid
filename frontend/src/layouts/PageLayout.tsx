import clsx from "clsx";
import { useLocation } from "react-router-dom";

interface Props {
  children: React.ReactNode;
}

export default function PageLayout({ children }: Props) {
  const { pathname } = useLocation();
  const isChatPages = pathname === "/" || pathname.startsWith("/letter");

  return (
    <div
      className={clsx(
        "flex justify-center pt-(--navbar-height)",
        isChatPages ? "h-dvh" : "items-center sm:pt-32 sm:pb-16",
      )}
      id="page-layout"
    >
      {children}
    </div>
  );
}
