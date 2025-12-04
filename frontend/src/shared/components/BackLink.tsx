import { Link } from "react-router-dom";

export default function BackLink() {
  return (
    <Link
      className="absolute top-4 left-4 flex text-[#4a90e2] hover:text-[#3a7bc8] font-semibold"
      to="/"
      aria-label="Go back"
    >
      <svg
        className="w-6 h-6 mr-2"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15 19l-7-7 7-7"
        />
      </svg>
      Back
    </Link>
  );
}
