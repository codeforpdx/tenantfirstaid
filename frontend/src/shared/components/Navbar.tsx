import { useState } from "react";
import { Link } from "react-router-dom";
import TenantFirstAidLogo from "./TenatFirstAidLogo";

export default function Navbar() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <nav className="fixed w-full bg-[#1F584F] shadow-md py-3 px-6 z-50">
      <div className="mx-auto flex items-center justify-between">
        <div className="flex items-center">
          <Link to="/">
            <TenantFirstAidLogo />
          </Link>
        </div>
        <button
          className="flex flex-col justify-center items-center w-10 h-10 relative z-60"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Open menu"
        >
          <span
            className={`block w-7 h-1 rounded transition-all duration-300 ${
              sidebarOpen
                ? "rotate-45 translate-y-2 bg-[#1F584F]"
                : "bg-[#BACAB2]"
            }`}
          />
          <span
            className={`block w-7 h-1 bg-[#BACAB2] rounded my-1 transition-all duration-300 ${
              sidebarOpen ? "opacity-0" : ""
            }`}
          />
          <span
            className={`block w-7 h-1 rounded transition-all duration-300 ${
              sidebarOpen
                ? "-rotate-45 -translate-y-2 bg-[#1F584F]"
                : "bg-[#BACAB2]"
            }`}
          />
        </button>
      </div>
      <div
        className={`fixed top-0 right-0 h-full w-64 bg-[#F4F4F2] shadow-lg z-50 transition-transform duration-300 ${
          sidebarOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex flex-col p-8 gap-6 mt-10">
          <Link
            to="/"
            className="block px-3 py-2 rounded text-gray-700 font-medium transition-colors hover:bg-[#4F8B82] hover:text-[#F4F4F2]"
            onClick={() => setSidebarOpen(false)}
          >
            Chat
          </Link>
          <Link
            to="/letter"
            className="block px-3 py-2 rounded text-gray-700 font-medium transition-colors hover:bg-[#4F8B82] hover:text-[#F4F4F2]"
            onClick={() => setSidebarOpen(false)}
          >
            Letter
          </Link>
          <Link
            to="/about"
            className="block px-3 py-2 rounded text-gray-700 font-medium transition-colors hover:bg-[#4F8B82] hover:text-[#F4F4F2]"
            onClick={() => setSidebarOpen(false)}
          >
            About Tenant First Aid
          </Link>
          <Link
            to="/disclaimer"
            className="block px-3 py-2 rounded text-gray-700 font-medium transition-colors hover:bg-[#4F8B82] hover:text-[#F4F4F2]"
            onClick={() => setSidebarOpen(false)}
          >
            Disclaimer
          </Link>
          <Link
            to="/privacy-policy"
            className="block px-3 py-2 rounded text-gray-700 font-medium transition-colors hover:bg-[#4F8B82] hover:text-[#F4F4F2]"
            onClick={() => setSidebarOpen(false)}
          >
            Privacy Policy
          </Link>
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
