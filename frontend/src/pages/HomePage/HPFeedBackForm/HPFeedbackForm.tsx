import { useState, ChangeEvent, FormEvent } from "react";
import sendHPFeedback from "./feedbackHPHelper";
import clsx from "clsx";

interface Props {
  nameValue: string;
  subjectValue: string;
  feedbackValue: string;
}

const inputClasses = clsx(
  "m-0 border-none outline-none",
  "bg-[#E6D5B8]/5 text-[#F4F4F2]",
  "p-4 text-base rounded-xl",
  "transition-colors duration-300 ease-in-out",
  "shadow-[inset_0_2px_4px_rgba(255,255,255,0.05),0_1px_3px_rgba(0,0,0,0.1),0_1px_2px_rgba(0,0,0,0.06)]",
  "focus:ring-0",
);

export default function HPFeedbackForm({
  nameValue,
  subjectValue,
  feedbackValue,
}: Props) {
  const [form, setForm] = useState({
    name: nameValue,
    subject: subjectValue,
    feedback: feedbackValue,
  });

  const handleChange = (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const result = await sendHPFeedback(form.name, form.subject, form.feedback);

    if (result.success) {
      setForm({ name: "", subject: "", feedback: "" });
    }
  };

  return (
    <section className="relative z-10 flex justify-center pb-[100px]">
      <form
        className="flex w-full max-w-[600px] flex-col gap-5 px-5"
        onSubmit={handleSubmit}
      >
        <input
          type="text"
          name="name"
          placeholder="Name"
          className={inputClasses}
          required
          value={form.name}
          onChange={handleChange}
        />
        <input
          type="text"
          name="subject"
          placeholder="Subject"
          className={inputClasses}
          required
          value={form.subject}
          onChange={handleChange}
        />
        <textarea
          name="feedback"
          placeholder="Message"
          className={clsx(inputClasses, "min-h-40 resize-y")}
          required
          value={form.feedback}
          onChange={handleChange}
        />

        <button
          type="submit"
          className={clsx(
            "m-0 cursor-pointer border-none rounded-xl p-4 transition-all duration-200 ease-in-out hover:opacity-90",
            "bg-[#E6D5B8]/70 text-[#00FF8F] text-[1.2rem] font-bold",
            "shadow-[0_4px_15px_rgba(16,185,129,0.3)]",
          )}
        >
          Submit
        </button>
      </form>
    </section>
  );
}
