interface Props {
  isOngoing: boolean;
  children: React.ReactNode;
}

export default function DisclaimerLayout({ isOngoing, children }: Props) {
  return (
    <div
      className={`container mx-auto text-xs px-4 text-center ${isOngoing ? "my-2" : "max-w-[600px] my-4"}`}
    >
      <p className={`${isOngoing ? "mb-0" : "mb-2"}`}>
        <strong>Disclaimer</strong>:&nbsp;
        {children}
        &nbsp;
        <span>
          For questions, contact{" "}
          <a href="mailto:michael@qiu-qiulaw.com" className="underline">
            michael@qiu-qiulaw.com
          </a>
        </span>
      </p>
    </div>
  );
}
