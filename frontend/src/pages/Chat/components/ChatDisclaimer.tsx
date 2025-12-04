import { Link } from "react-router-dom";
import DisclaimerLayout from "../../../shared/components/DisclaimerLayout";
import { CONTACT_EMAIL } from "../../../shared/constants/constants";

interface Props {
  isOngoing: boolean;
}

export default function ChatDisclaimer({ isOngoing }: Props) {
  const disclaimer = isOngoing ? (
    <span>
      Tenant First Aid offers general information about Oregon housing law and
      creates letters based on information provided by the user. Information and
      letters provided here are not legal advice - for more information, see
      our&nbsp;
      <Link
        to="/about"
        target="_blank"
        rel="noopener noreferrer"
        className="underline"
        aria-label="to about page"
      >
        About page
      </Link>
      . For help with your specific situation, contact a qualified attorney. For
      questions regarding Tenant First Aid or any information provided or
      discussed, you can contact&nbsp;
      <a
        href={`mailto:${CONTACT_EMAIL}`}
        className="underline"
        aria-label="contact-email"
      >
        {CONTACT_EMAIL}
      </a>
      &nbsp;using the Feedback button.
    </span>
  ) : (
    <span>
      The information provided by this chatbot is general information only and
      does not constitute legal advice. While Tenant First Aid strives to keep
      the content accurate and up to date, completeness and accuracy is not
      guaranteed. If you have a specific legal issue or question, consider
      contacting a qualified attorney or a local legal aid clinic for
      personalized assistance. For questions related to Tenant First Aid,
      contact&nbsp;
      <a
        href={`mailto:${CONTACT_EMAIL}`}
        className="underline"
        aria-label="contact-email"
      >
        {CONTACT_EMAIL}
      </a>
      .
    </span>
  );

  return (
    <DisclaimerLayout isOngoing={isOngoing}>{disclaimer}</DisclaimerLayout>
  );
}
