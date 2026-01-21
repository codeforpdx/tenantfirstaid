const HEADING_SIZES = {
  2: "text-2xl",
  3: "text-xl",
};

interface Props {
  title: React.ReactNode;
  headingLevel: 2 | 3;
  children: React.ReactNode;
  className?: string;
}

export default function PageSection({
  title,
  headingLevel,
  children,
  className = "",
}: Props) {
  const HeadingTag = `h${headingLevel}` as "h2" | "h3";

  return (
    <>
      <HeadingTag
        className={`${HEADING_SIZES[headingLevel]} font-semibold mt-6 mb-2`}
      >
        {title}
      </HeadingTag>
      <div className={className} id="section-content">
        {children}
      </div>
    </>
  );
}
