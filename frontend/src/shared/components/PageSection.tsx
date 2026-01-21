interface Props {
  title: React.ReactNode;
  headingLevel: 2 | 3;
  subheader?: string;
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
  const headingSize = {
    2: "text-2xl",
    3: "text-xl",
  };

  return (
    <>
      <HeadingTag
        className={`${headingSize[headingLevel]} font-semibold mt-6 mb-2`}
      >
        {title}
      </HeadingTag>
      <div className={className}>{children}</div>
    </>
  );
}
