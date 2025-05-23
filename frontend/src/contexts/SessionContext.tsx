import { createContext, useMemo, useState } from "react";
import generateSessionId from "../pages/Chat/utils/sessionHelper";

interface ISessionContextType {
  sessionId: string;
  setSessionId: React.Dispatch<React.SetStateAction<string>>;
  handleNewSession: () => Promise<void>;
}

const SessionContext = createContext<ISessionContextType | null>(null);

export { SessionContext };

interface Props {
  children: React.ReactNode;
}

export default function SessionContextProvider({ children }: Props) {
  const [sessionId, setSessionId] = useState("");

  const handleNewSession = async () => {
    const newSessionId = generateSessionId();
    localStorage.setItem("sessionId", newSessionId);
    setSessionId(newSessionId);
  };

  const sessionContextObject = useMemo(
    () => ({ sessionId, setSessionId, handleNewSession }),
    [sessionId]
  );

  return (
    <SessionContext.Provider value={sessionContextObject}>
      {children}
    </SessionContext.Provider>
  );
}
