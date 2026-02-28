import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import TenantFirstAidLogo from "../TenantFirstAidLogo";
import NavbarMenuButton from "./NavbarMenuButton";
import Sidebar from "./Sidebar";
import { useIsMobile } from "../../../hooks/useIsMobile";
import { NAVBAR_LINKS } from "../../constants/constants";
import clsx from "clsx";

export default function Navbar() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const isMobile = useIsMobile();

  return (
    <nav className="fixed w-full bg-green-dark shadow-md py-3 px-6 z-50">
      <div className="mx-auto flex items-center justify-between">
        <div className="flex items-center">
          <Link to="/">
            <TenantFirstAidLogo />
          </Link>
        </div>
        {isMobile ? (
          <NavbarMenuButton
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
          />
        ) : (
          <div className="flex gap-3">
            {NAVBAR_LINKS.map(({ label, to }) => (
              <NavLink
                to={to}
                key={label}
                className={({ isActive }) =>
                  clsx(
                    "px-2 text-paper-background",
                    "hover:text-green-dark hover:bg-green-light hover:opacity-70",
                    "hover:outline hover:outline-paper-background hover:rounded",
                    "no-underline",
                    isActive && "bg-green-medium rounded",
                  )
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        )}
      </div>
      {isMobile && (
        <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      )}
    </nav>
  );
}
