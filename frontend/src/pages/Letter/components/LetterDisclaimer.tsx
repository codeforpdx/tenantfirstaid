import { Link } from "react-router-dom";
import DisclaimerLayout from "../../../shared/components/DisclaimerLayout";
import { CONTACT_EMAIL } from "../../../shared/constants/constants";

interface Props {
  isOngoing: boolean;
}

export default function LetterDisclaimer({ isOngoing }: Props) {
  const disclaimer = isOngoing ? (
    <span>
      This tool provides general information and drafts letters based solely on
      what you enter. It is not legal advice and does not create an
      attorney–client relationship. As explained further in the&nbsp;
      <Link
        to="/privacy-policy"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="to privacy policy"
        className="hover:text-gray-dark"
      >
        Privacy Policy
      </Link>
      , we do not save any data from these conversations, but you can enter your
      personal information into the chatbox and it will appear in the
      corresponding brackets of the letter. For questions regarding Tenant First
      Aid or any information provided or discussed, you can contact&nbsp;
      <a
        href={`mailto:${CONTACT_EMAIL}`}
        aria-label="contact-email"
        className="hover:text-gray-dark"
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
        aria-label="contact-email"
        className="hover:text-gray-dark"
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
