import { use } from "react";
import { SessionContext } from "../contexts/SessionContext";

export default function useSession() {
  const context = use(SessionContext);
  if (context === null) {
    throw new Error(
      "useSession can only be used within SessionContextProvider"
    );
  }
  return context;
}
