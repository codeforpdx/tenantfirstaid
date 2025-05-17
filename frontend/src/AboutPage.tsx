import { useNavigate } from "react-router-dom";

export default function AboutPage() {
    const navigate = useNavigate();

    return (
        <div className="max-w-2xl mx-auto my-8 p-8 bg-white rounded-lg shadow-md relative ">
            <button
                className="absolute top-2 left-4 flex items-center text-[#4a90e2] hover:text-[#3a7bc8] font-semibold cursor-pointer"
                onClick={() => navigate(-1)}
                aria-label="Go back"
            >
                <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
                Back
            </button>
            <h1 className="text-3xl font-bold mb-4 text-gray-800 mt-4 text-center">Tenant First Aid</h1>
            <p className="mb-6 text-gray-700">
                <strong>Tenant First Aid</strong> is an AI-powered chatbot designed to help tenants navigate rental issues, answer questions, and provides legal advice related to housing and eviction.
            </p>
            <h2 className="text-2xl font-semibold mt-6 mb-2 text-gray-800">Features</h2>
            <ul className="list-disc list-inside mb-6 text-gray-700">
                <li>Instant answers to common rental questions</li>
                <li>Guidance on tenant rights and landlord obligations</li>
                <li>Easy-to-use chat interface</li>
                <li>Available 24/7</li>
            </ul>
            <h2 className="text-2xl font-semibold mt-6 mb-2 text-gray-800">How It Works</h2>
            <p className="mb-6 text-gray-700">
                Simply type your question or describe your situation, and Tenant First Aid will provide helpful information or direct you to relevant resources.
            </p>
            <h2 className="text-2xl font-semibold mt-6 mb-2 text-gray-800">Disclaimer</h2>
            <p className="text-gray-600">
                TenantFirst is an AI assistant and does not provide legal advice. For complex or urgent legal matters, please consult a qualified professional.
            </p>
        </div>
    );
}