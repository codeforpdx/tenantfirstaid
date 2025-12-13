import { useState } from "react";
import { Link } from "react-router-dom";
import TenantFirstAidLogo from "../TenantFirstAidLogo";
import NavbarMenuButton from "./NavbarMenuButton";
import { NAVBAR_LINKS } from "../../constants/constants";

export default function Navbar() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <nav className="fixed w-full bg-green-dark shadow-md py-3 px-6 z-50">
      <div className="mx-auto flex items-center justify-between">
        <div className="flex items-center">
          <Link to="/">
            <TenantFirstAidLogo />
          </Link>
        </div>
        <NavbarMenuButton
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
        />
      </div>
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
            <Link
              to={to}
              key={label}
              className={`
                block px-3 py-2
                rounded no-underline
                text-gray-dark font-medium hover:text-paper-background
                transition-colors
                hover:bg-green-medium`}
              onClick={() => setSidebarOpen(false)}
            >
              {label}
            </Link>
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
    </nav>
  );
}
