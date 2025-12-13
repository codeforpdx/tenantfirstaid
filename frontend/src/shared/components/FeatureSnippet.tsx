import { REFERENCED_LAW_LIST } from "../constants/constants";

export default function FeatureSnippet() {
  return (
    <div className="flex lg:flex-col justify-center gap-4 pt-4 px-4 sm:pb-4 md:pb-0">
      <div className="w-full">
        <h2 className="text-xl">Features</h2>
        <ul className="list-disc pl-4">
          <li>Instant answers to common rental questions</li>
          <li>Guidance on tenant rights and landlord obligations</li>
          <li>Easy-to-use chat interface</li>
          <li>Available 24/7</li>
        </ul>
      </div>
      <div className="w-full">
        <p>Powered by Google's Gemini 2.5 Pro</p>
        <p>Laws referenced by Tenant First Aid:</p>
        <ul className="list-disc pl-4">
          {Object.entries(REFERENCED_LAW_LIST).map(([key, reference]) => (
            <li key={key}>
              <a
                href={reference.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-link hover:text-blue-dark"
              >
                {reference.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
