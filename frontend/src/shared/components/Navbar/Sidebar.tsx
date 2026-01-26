import { NavLink } from "react-router-dom";
import { NAVBAR_LINKS } from "../../constants/constants";

interface Props {
  sidebarOpen: boolean;
  setSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function Sidebar({ sidebarOpen, setSidebarOpen }: Props) {
  return (
    <>
      <div
        className={`
          fixed top-0 right-0
          h-full w-64
          bg-paper-background
          shadow-lg z-50
          transition-transform duration-300
          ${sidebarOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="flex flex-col p-8 gap-6 mt-10">
          {NAVBAR_LINKS.map(({ to, label }) => (
            <NavLink
              to={to}
              key={label}
              className={({ isActive }) =>
                `block px-3 py-2
                rounded no-underline
                text-gray-dark font-medium hover:text-paper-background
                transition-colors
                hover:bg-green-medium
                ${isActive ? "bg-green-background text-gray-dark " : ""}`
              }
              onClick={() => setSidebarOpen(false)}
            >
              {label}
            </NavLink>
          ))}
          <hr className="my-2 border-t border-gray-300" />
        </div>
      </div>
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </>
  );
}
