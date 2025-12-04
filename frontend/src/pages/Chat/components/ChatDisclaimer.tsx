import DisclaimerLayout from "../../../shared/components/DisclaimerLayout";

interface Props {
  isOngoing: boolean;
}

export default function ChatDisclaimer({ isOngoing }: Props) {
  const disclaimer = isOngoing ? (
    <span>
      This chatbot offers general housing law info and is not legal advice. For
      help with your situation, contact a lawyer.
    </span>
  ) : (
    <span>
      The information provided by this chatbot is general information only and
      does not constitute legal advice. While Tenant First Aid strives to keep
      the content accurate and up to date, completeness and accuracy is not
      guaranteed. If you have a specific legal issue or question, consider
      contacting a qualified attorney or a local legal aid clinic for
      personalized assistance.
    </span>
  );

  return (
    <DisclaimerLayout isOngoing={isOngoing}>{disclaimer}</DisclaimerLayout>
  );
}
