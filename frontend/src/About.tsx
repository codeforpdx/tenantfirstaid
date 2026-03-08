import BackLink from "./shared/components/BackLink";
import PageSection from "./shared/components/PageSection";
import { CONTACT_EMAIL } from "./shared/constants/constants";

export default function About() {
  return (
    <div className="relative max-w-2xl m-auto p-8 bg-paper-background rounded-none sm:rounded-lg shadow-md">
      <BackLink />

      <PageSection
        title="About Tenant First Aid"
        headingLevel={2}
        className="space-y-4"
      >
        <p>
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
        <p>
          It&apos;s called "Tenant First Aid" because it&apos;s like emergency
          help for renters facing eviction—quick, clear, and focused on what to
          do right now. Just like medical first aid helps stabilize someone
          before they can see a doctor, Tenant First Aid gives Oregon tenants
          the essential legal info they need to understand an eviction notice,
          respond on time, and avoid mistakes that could cost them their home.
        </p>
      </PageSection>

      <PageSection title="Contact" headingLevel={2}>
        <div className="flex flex-col">
          <span>Michael Zhang</span>
          <span>Attorney, licensed in Oregon and Washington</span>
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="underline text-blue-link hover:text-blue-dark"
            aria-label="contact-email"
          >
            {CONTACT_EMAIL}
          </a>
        </div>
      </PageSection>

      <PageSection title="How It Works" headingLevel={2} className="space-y-4">
        <p>
          Simply type your question or describe your situation, and Tenant First
          Aid will provide helpful information or direct you to relevant
          resources.
        </p>
      </PageSection>

      <PageSection title="Data Usage" headingLevel={2} className="space-y-4">
        <p>
          Tenant First Aid does not store any personal data. All interactions
          are processed in real-time and not saved for future use.
        </p>
      </PageSection>

      <PageSection
        title="Legal Disclaimer & Privacy Notice"
        headingLevel={2}
        className="space-y-4"
      >
        <p>
          This chatbot provides general information about eviction law in Oregon
          and creates letters based on information provided by the user.
        </p>
        <p>
          It is not legal advice, and using it does not create an
          attorney-client relationship. If you need legal advice or
          representation, you should contact a licensed attorney.
        </p>
      </PageSection>

      <PageSection
        title="Information Accuracy"
        headingLevel={2}
        className="space-y-4"
      >
        <p>
          We try to keep the information up-to-date and accurate, but eviction
          laws can change. We cannot guarantee that everything on this site or
          through this chatbot is current, complete, or applies to your specific
          situation.
        </p>
      </PageSection>

      <PageSection title="No Liability" headingLevel={2}>
        <p>
          We are not responsible for any decisions you make based on information
          from this chatbot. Use it at your own risk. Always double-check with a
          legal aid organization or attorney.
        </p>
      </PageSection>
    </div>
  );
}
