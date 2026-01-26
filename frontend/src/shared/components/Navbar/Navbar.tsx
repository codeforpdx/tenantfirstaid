import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import TenantFirstAidLogo from "../TenantFirstAidLogo";
import NavbarMenuButton from "./NavbarMenuButton";
import Sidebar from "./Sidebar";
import { useIsMobile } from "../../../hooks/useIsMobile";
import { NAVBAR_LINKS } from "../../constants/constants";

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
                  `px-2
                  text-paper-background hover:text-green-dark
                  hover:bg-green-light
                  hover:outline hover:outline-paper-background hover:rounded
                  hover:opacity-70 no-underline
                  ${isActive ? "bg-green-medium text-paper-background rounded" : "no-underline"}`
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
