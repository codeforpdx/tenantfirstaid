import { useNavigate } from "react-router-dom";

export default function AboutPage() {
  const navigate = useNavigate();

  return (
    <div className="mt-26 max-w-2xl mx-auto my-8 p-8 bg-white rounded-lg shadow-md relative ">
      <button
        className="absolute top-2 left-4 flex items-center text-[#4a90e2] hover:text-[#3a7bc8] font-semibold cursor-pointer"
        onClick={() => navigate(-1)}
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
      </button>
      <h1 className="text-3xl font-bold mb-4 text-gray-800 mt-4 text-center">
        Tenant First Aid
      </h1>
      <p className="mb-6 text-gray-700">
        <strong>Tenant First Aid</strong> is an AI-powered chatbot designed to
        help Oregon tenants navigate housing and eviction issues. It is a
        volunteer-built program by{" "}
        <a href="https://www.codepdx.org/" className="text-blue-700 underline">
          Code PDX
        </a>{" "}
        and{" "}
        <a
          href="https://www.qiu-qiulaw.com/"
          className="text-blue-700 underline"
        >
          Qiu Qiu Law
        </a>
        .
      </p>
      <p className="mb-6 text-gray-700">
        It&apos;s called "Tenant First Aid" because it&apos;s like emergency
        help for renters facing eviction—quick, clear, and focused on what to do
        right now. Just like medical first aid helps stabilize someone before
        they can see a doctor, Tenant First Aid gives Oregon tenants the
        essential legal info they need to understand an eviction notice, respond
        on time, and avoid mistakes that could cost them their home.
      </p>
      <h2 className="text-2xl font-semibold mt-6 mb-2 text-gray-800">
        Contact:
      </h2>
      <p>Michael Zhang</p>
      <p>Attorney, licensed in Oregon and Washington</p>
      <p>michael@qiu-qiulaw.com</p>
      <h2 className="text-2xl font-semibold mt-6 mb-2 text-gray-800">
        Features
      </h2>
      <ul className="list-disc list-inside mb-6 text-gray-700">
        <li>Instant answers to common rental questions</li>
        <li>Guidance on tenant rights and landlord obligations</li>
        <li>Easy-to-use chat interface</li>
        <li>Available 24/7</li>
      </ul>
      <h2 className="text-2xl font-semibold mt-6 mb-2 text-gray-800">
        How It Works
      </h2>
      <p className="mb-6 text-gray-700">
        Simply type your question or describe your situation, and Tenant First
        Aid will provide helpful information or direct you to relevant
        resources.
      </p>
      <h2 className="text-2xl font-semibold mt-6 mb-2 text-gray-800">Quick Facts:</h2>
      <ul className="list-disc list-inside mb-6 text-gray-700">
        <li>Uses openAI ChatGPT o3 model</li>
        <li>
          Reference library:
          <ul className="list-none pl-6 mt-1">
            <li>
              <a href="https://www.oregonlegislature.gov/bills_laws/ors/ors090.html" className="text-blue-700 underline">
                ORS 90 (as amended 2023)
              </a>
            </li>
            <li>
              <a href="https://www.oregonlegislature.gov/bills_laws/ors/ors105.html" className="text-blue-700 underline">
                ORS 105
              </a>
            </li>
            <li>
              <a href="https://eugene.municipal.codes/EC/8.425" className="text-blue-700 underline">
                Eugene Code Section 8.425
              </a>
            </li>
            <li>
              <a href="https://www.portland.gov/code/30/all" className="text-blue-700 underline">
                Portland City Code Title 30
              </a>
            </li>
          </ul>
        </li>
      </ul>
    </div>
  );
}
