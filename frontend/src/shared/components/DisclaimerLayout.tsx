interface Props {
  isOngoing: boolean;
  children: React.ReactNode;
}

export default function DisclaimerLayout({ isOngoing, children }: Props) {
  return (
    <div
      className={`container mx-auto text-xs ${isOngoing ? "" : "max-w-[600px]"}`}
    >
      <p>
        <strong>Disclaimer</strong>:&nbsp;
        {children}
      </p>
    </div>
  );
}
