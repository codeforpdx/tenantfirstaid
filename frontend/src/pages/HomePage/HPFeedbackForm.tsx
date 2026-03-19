import { useState } from "react";
import sendHPFeedback from "./feedbackHPHelper";

interface Props {
  nameValue: string;
  subjectValue: string;
  feedbackValue: string;
}

export default function HPFeedbackForm({ nameValue, subjectValue, feedbackValue }: Props) {
  const [name, setName] = useState(nameValue);
  const [subject, setSubject] = useState(subjectValue);
  const [feedback, setFeedback] = useState(feedbackValue);
  
  return (
    <section className="relative z-[3] flex justify-center pb-[100px]">
      <form 
        className="flex w-full max-w-[600px] flex-col gap-[20px] px-[20px]" 
        onSubmit={(event) => {
          event.preventDefault(); 
          sendHPFeedback(name, subject, feedback);
          
          setName("");
          setSubject("");
          setFeedback("");
        }}
      >
        <input 
          type="text" 
          name="name" 
          placeholder="Name" 
          className="m-0 border-none bg-[rgba(230,213,184,0.05)] p-[16px] text-[1rem] text-[#F4F4F2] outline-none rounded-[12px] transition-colors duration-[300ms] ease-in-out shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),_0_1px_3px_rgba(0,0,0,0.1),_0_1px_2px_rgba(0,0,0,0.06)] focus:outline-none focus:ring-0" 
          required
          value={name}
          onChange={(event) => setName(event.target.value)} 
        />
        <input 
          type="text" 
          name="subject" 
          placeholder="Subject" 
          className="m-0 border-none bg-[rgba(230,213,184,0.05)] p-[16px] text-[1rem] text-[#F4F4F2] outline-none rounded-[12px] transition-colors duration-[300ms] ease-in-out shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),_0_1px_3px_rgba(0,0,0,0.1),_0_1px_2px_rgba(0,0,0,0.06)] focus:outline-none focus:ring-0" 
          required
          value={subject}
          onChange={(event) => setSubject(event.target.value)} 
        />
        <textarea 
          name="message" 
          placeholder="Message" 
          className="m-0 min-h-[160px] resize-y border-none bg-[rgba(230,213,184,0.05)] p-[16px] text-[1rem] text-[#F4F4F2] outline-none rounded-[12px] transition-colors duration-[300ms] ease-in-out shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),_0_1px_3px_rgba(0,0,0,0.1),_0_1px_2px_rgba(0,0,0,0.06)] focus:outline-none focus:ring-0" 
          required
          value={feedback}
          onChange={(event) => setFeedback(event.target.value)}
        ></textarea>
        
        <button 
          type="submit" 
          className="m-0 cursor-pointer border-none bg-[rgba(230,213,184,0.7)] p-[16px] text-[1.2rem] font-bold text-[rgb(0,255,143)] rounded-[12px] shadow-[0_4px_15px_rgba(16,185,129,0.3)] transition-all duration-[200ms] ease-in-out hover:opacity-90"
        >
          Submit
        </button>
      </form>
    </section>
  );
}