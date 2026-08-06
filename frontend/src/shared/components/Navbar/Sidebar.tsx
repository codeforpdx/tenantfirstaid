import { NavLink } from "react-router";
import { NAVBAR_LINKS, NAVBAR_FEATURES } from "../../constants/constants";
import useActiveJurisdiction from "../../../hooks/useActiveJurisdiction";
import { pathFor } from "../../utils/jurisdiction";
import clsx from "clsx";

interface Props {
  sidebarOpen: boolean;
  setSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function Sidebar({ sidebarOpen, setSidebarOpen }: Props) {
  const { active } = useActiveJurisdiction();

  return (
    <>
      <div
        className={clsx(
          "fixed top-0 right-0 bottom-(--footer-height)",
          "w-64",
          "bg-paper-background shadow-lg",
          "z-50 transition-transform duration-300",
          sidebarOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex flex-col p-8 gap-6 mt-10">
          {NAVBAR_FEATURES.map(({ label, feature }) => (
            <NavLink
              to={pathFor(feature, active)}
              key={label}
              className={({ isActive }) =>
                clsx(
                  "block px-3 py-2 rounded no-underline text-gray-dark font-medium hover:text-paper-background transition-colors hover:bg-green-medium",
                  isActive && "bg-green-background",
                )
              }
              onClick={() => setSidebarOpen(false)}
            >
              {label}
            </NavLink>
          ))}
          {NAVBAR_LINKS.map(({ to, label }) => (
            <NavLink
              to={to}
              key={label}
              className={({ isActive }) =>
                clsx(
                  "block px-3 py-2 rounded no-underline text-gray-dark font-medium hover:text-paper-background transition-colors hover:bg-green-medium",
                  isActive && "bg-green-background",
                )
              }
              onClick={() => setSidebarOpen(false)}
            >
              {label}
            </NavLink>
          ))}
        </div>
      </div>
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-[45]"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </>
  );
}
