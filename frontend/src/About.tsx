import BackLink from "./shared/components/BackLink";
import { CONTACT_EMAIL } from "./shared/constants/constants";

export default function About() {
  return (
    <div className="flex items-center pt-16 sm:pt-32 sm:pb-16">
      <div className="relative max-w-2xl m-auto p-8 bg-paper-background rounded-none sm:rounded-lg shadow-md">
        <BackLink />
        <h2 className="text-2xl font-semibold mt-6 mb-2">
          About Tenant First Aid
        </h2>
        <p className="mb-6">
          <strong>Tenant First Aid</strong> is an AI-powered chatbot designed to
          help Oregon tenants navigate housing and eviction issues. It is a
          volunteer-built program by{" "}
          <a
            href="https://www.codepdx.org/"
            className="text-blue-link hover:text-blue-dark"
          >
            Code PDX
          </a>{" "}
          and{" "}
          <a
            href="https://www.qiu-qiulaw.com/"
            className="text-blue-link hover:text-blue-dark"
          >
            Qiu Qiu Law
          </a>
          .
        </p>
        <p className="mb-6">
          It&apos;s called "Tenant First Aid" because it&apos;s like emergency
          help for renters facing eviction—quick, clear, and focused on what to
          do right now. Just like medical first aid helps stabilize someone
          before they can see a doctor, Tenant First Aid gives Oregon tenants
          the essential legal info they need to understand an eviction notice,
          respond on time, and avoid mistakes that could cost them their home.
        </p>
        <h2 className="text-2xl font-semibold mt-6 mb-2">Contact:</h2>
        <p>Michael Zhang</p>
        <p>Attorney, licensed in Oregon and Washington</p>
        <p>{CONTACT_EMAIL}</p>
        <h2 className="text-2xl font-semibold mt-6 mb-2">How It Works</h2>
        <p className="mb-6">
          Simply type your question or describe your situation, and Tenant First
          Aid will provide helpful information or direct you to relevant
          resources.
        </p>
        <h2 className="text-2xl font-semibold mt-6 mb-2">Data Usage</h2>
        <p className="mb-6">
          Tenant First Aid does not store any personal data. All interactions
          are processed in real-time and not saved for future use.
        </p>
        <h2 className="text-2xl font-semibold mt-6 mb-2">
          Legal Disclaimer & Privacy Notice
        </h2>
        <p className="mb-6">
          This chatbot provides general information about eviction law in Oregon
          and creates letters based on information provided by the user.
        </p>
        <p>
          It is not legal advice, and using it does not create an
          attorney-client relationship. If you need legal advice or
          representation, you should contact a licensed attorney.
        </p>
        <h2 className="text-2xl font-semibold mt-6 mb-2">
          Information Accuracy
        </h2>
        <p className="mb-6">
          We try to keep the information up-to-date and accurate, but eviction
          laws can change. We cannot guarantee that everything on this site or
          through this chatbot is current, complete, or applies to your specific
          situation.
        </p>
        <h2 className="text-2xl font-semibold mt-6 mb-2">No Liability</h2>
        <p>
          We are not responsible for any decisions you make based on information
          from this chatbot. Use it at your own risk. Always double-check with a
          legal aid organization or attorney.
        </p>
      </div>
    </div>
  );
}
