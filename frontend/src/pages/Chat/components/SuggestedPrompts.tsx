interface SuggestedPromptsProps {
  onPromptClick: (prompt: string) => void;
}

const prompts = [
  "Do I qualify for a rental subsidy, such as Section 8/HomeForward?",
  "I have a leak in my roof. Help me address this with my landlord.",
  "I received an eviction notice for non-payment of rent. What should I do?",
  "I received a 'no-cause' eviction notice. How much money is my landlord required to pay me to move out?",
  "If my landlord put my security deposit in an interest-bearing account, are they required to give me the interest when I move out?",
];

export default function SuggestedPrompts({
  onPromptClick,
}: SuggestedPromptsProps) {
  return (
    <div className="items-center m-auto max-w-[650px]" role="region" aria-label="Suggested questions">
      <div className="flex flex-col gap-4 fade-in-up items-center">
        {prompts.map((prompt, idx) => (
          <button
            key={idx}
            className="inline-flex px-4 border border-[#1f584f] rounded-4xl cursor-pointer py-1 font-medium sm:bg-white hover:bg-[#bac9b2]/50"
            onClick={() =>
              onPromptClick(Array.isArray(prompt) ? prompt.join(" ") : prompt)
            }
            type="button"
            aria-label={`Use suggested prompt: ${prompt}`}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
