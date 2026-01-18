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
        "flex items-center justify-center pt-16",
        isChatPages ? "h-screen" : "sm:pt-32 sm:pb-16",
      )}
      id="page-layout"
    >
      {children}
    </div>
  );
}
