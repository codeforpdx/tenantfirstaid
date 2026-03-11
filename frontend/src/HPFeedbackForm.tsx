import { useState } from "react";
import sendHPFeedback from "./pages/Chat/utils/feedbackHPHelper";

const styles = {
  formSection: { display: 'flex', justifyContent: 'center', paddingBottom: '100px', position: 'relative', zIndex: 3 },
  contactForm: { display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', maxWidth: '600px', padding: '0 20px' },
  formInput: { padding: '16px', borderRadius: '12px', border: '1px solid rgba(230, 213, 184, 0.2)', backgroundColor: 'rgba(230, 213, 184, 0.05)', color: '#F4F4F2', fontSize: '1rem', outline: 'none', transition: 'border-color 0.3s ease' },
  formTextarea: { padding: '16px', borderRadius: '12px', border: '1px solid rgba(230, 213, 184, 0.2)', backgroundColor: 'rgba(230, 213, 184, 0.05)', color: '#F4F4F2', fontSize: '1rem', outline: 'none', minHeight: '160px', resize: 'vertical', transition: 'border-color 0.3s ease' },
  formSubmit: { padding: '16px', backgroundColor: 'rgba(230, 213, 184, 0.7)', color: 'rgb(0, 255, 143)', fontWeight: 'bold', fontSize: '1.2rem', border: 'none', borderRadius: '12px', cursor: 'pointer', transition: 'transform 0.2s ease, box-shadow 0.2s ease', boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)' }
} as const;

interface Props {
  nameValue: string;
  subjectValue: string;
  feedbackValue: string;
}

/**
 * Dialog for submitting feedback with optional email CC and word redaction.
 */
export default function HPFeedbackForm({ nameValue, subjectValue, feedbackValue }: Props) {
  const [name, setName] = useState(nameValue);
  const [subject, setSubject] = useState(subjectValue);
  const [feedback, setFeedback] = useState(feedbackValue);

  return (
      <section style={styles.formSection}>
        <form style={styles.contactForm}>
          <input type="text" name="name" placeholder="Name" style={styles.formInput} required
          onChange={(event) => setName(event.target.value)} />
          <input type="text" name="subject" placeholder="Subject" style={styles.formInput} required
          onChange={(event) => setSubject(event.target.value)} />
          <textarea name="message" placeholder="Message" style={styles.formTextarea} required
          onChange={(event) => setFeedback(event.target.value)}></textarea>
          <button type="submit" className="btn-hover" style={styles.formSubmit}
          onClick={() => {
            setTimeout(() => {
              sendHPFeedback(name, subject, feedback);
            }, 1000);
          }}>Submit</button>
        </form>
      </section>
  );
}
