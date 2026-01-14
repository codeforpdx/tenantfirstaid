import { useLocation } from "react-router-dom";

const chatPages = ["/", "/letter"];

interface Props {
  children: React.ReactNode;
}

export default function PageLayout({ children }: Props) {
  const { pathname } = useLocation();
  const isChatPages = chatPages.includes(pathname);

  return (
    <div
      className={`
        flex items-center justify-center pt-16
        ${isChatPages ? "h-screen" : "sm:pt-32 sm:pb-16"}
        `}
    >
      {children}
    </div>
  );
}
