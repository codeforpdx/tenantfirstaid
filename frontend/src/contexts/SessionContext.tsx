import { createContext, useMemo } from "react";

interface ISessionContextType {
  handleNewSession: () => Promise<void>;
}

const SessionContext = createContext<ISessionContextType | null>(null);

export { SessionContext };

interface Props {
  children: React.ReactNode;
}

export default function SessionContextProvider({ children }: Props) {
  const handleNewSession = async () => {
    // Clear the session by making a request to clear server-side session
    try {
      await fetch('/api/clear-session', {
        method: 'POST',
        credentials: 'include'
      });
      // Refresh the page to start fresh
      window.location.reload();
    } catch (error) {
      console.error('Failed to clear session:', error);
      // Fallback: just refresh the page
      window.location.reload();
    }
  };

  const sessionContextObject = useMemo(
    () => ({ handleNewSession }),
    []
  );

  return (
    <SessionContext.Provider value={sessionContextObject}>
      {children}
    </SessionContext.Provider>
  );
}
