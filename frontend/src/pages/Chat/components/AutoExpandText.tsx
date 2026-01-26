interface Props {
  isExpanded: boolean;
  children: React.ReactNode;
}

export default function AutoExpandText({ isExpanded, children }: Props) {
  return (
    <div
      className={`grid transition-all duration-300 ease-in-out
            ${
              isExpanded
                ? "grid-rows-[1fr] opacity-100 pt-2"
                : "grid-rows-[0fr] opacity-0"
            }
        `}
    >
      <div className="overflow-hidden px-4">{children}</div>
    </div>
  );
}
