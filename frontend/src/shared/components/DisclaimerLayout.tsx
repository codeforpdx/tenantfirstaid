interface Props {
  isOngoing: boolean;
  children: React.ReactNode;
}

export default function DisclaimerLayout({ isOngoing, children }: Props) {
  return (
    <div
      className={`container mx-auto text-xs px-4 text-center ${isOngoing ? "my-2" : "max-w-[600px] my-4"}`}
    >
      <p>
        <strong>Disclaimer</strong>:&nbsp;
        {children}
      </p>
    </div>
  );
}
