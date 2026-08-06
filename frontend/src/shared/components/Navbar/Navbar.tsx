import { useState } from "react";
import { Link, NavLink, useLocation } from "react-router";
import TenantFirstAidLogo from "../TenantFirstAidLogo";
import NavbarMenuButton from "./NavbarMenuButton";
import NavbarLocationMenu from "./NavbarLocationMenu";
import Sidebar from "./Sidebar";
import { useIsMobile } from "../../../hooks/useIsMobile";
import useActiveJurisdiction from "../../../hooks/useActiveJurisdiction";
import { NAVBAR_LINKS, NAVBAR_FEATURES } from "../../constants/constants";
import { pathFor } from "../../utils/jurisdiction";
import clsx from "clsx";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    "px-2 text-paper-background",
    "hover:text-green-dark hover:bg-green-light hover:opacity-70",
    "hover:outline hover:outline-paper-background hover:rounded",
    "no-underline",
    isActive && "bg-green-medium rounded",
  );

export default function Navbar() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const isMobile = useIsMobile();
  const { active } = useActiveJurisdiction();
  const { pathname } = useLocation();

  // The location picker drives the Chat/Letter links, so show it on the home
  // page and the feature routes, but not on static pages like /about.
  const showLocationMenu =
    pathname === "/" ||
    pathname.startsWith("/chat") ||
    pathname.startsWith("/letter");

  return (
    <nav className="fixed w-full bg-green-dark shadow-md py-3 px-6 z-50">
      <div className="mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/">
            <TenantFirstAidLogo />
          </Link>
          {showLocationMenu && <NavbarLocationMenu />}
        </div>
        {isMobile ? (
          <NavbarMenuButton
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
          />
        ) : (
          <div className="flex gap-3 items-center">
            {NAVBAR_FEATURES.map(({ label, feature }) => (
              <NavLink
                to={pathFor(feature, active)}
                key={label}
                className={navLinkClass}
              >
                {label}
              </NavLink>
            ))}
            {NAVBAR_LINKS.map(({ label, to }) => (
              <NavLink to={to} key={label} className={navLinkClass}>
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
