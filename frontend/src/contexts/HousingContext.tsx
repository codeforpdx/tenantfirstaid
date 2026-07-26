import { createContext, useCallback, useMemo, useState } from "react";
import DOMPurify, { SANITIZE_USER_SETTINGS } from "../shared/utils/dompurify";
import type { Location } from "../types/models";
import type { JurisdictionKey } from "../shared/constants/jurisdictions";

export interface HousingContextType {
  housingLocation: Location;
  city: JurisdictionKey | null;
  issueDescription: string;
  handleHousingLocation: ({ city, state }: Location) => void;
  handleCityChange: (option: JurisdictionKey | null) => void;
  handleIssueDescription: (
    event: React.ChangeEvent<HTMLTextAreaElement>,
  ) => void;
  handleFormReset: () => void;
}

const HousingContext = createContext<HousingContextType | null>(null);

interface Props {
  children: React.ReactNode;
}

export default function HousingContextProvider({ children }: Props) {
  const [city, setCity] = useState<JurisdictionKey | null>(null);
  const [housingLocation, setHousingLocation] = useState<Location>({
    city: null,
    state: null,
  });
  const [issueDescription, setIssueDescription] = useState("");

  const handleHousingLocation = useCallback(({ newCity, state }: Location) => {
    setHousingLocation({ city: newCity, state });
  }, []);

  const handleCityChange = useCallback((option: JurisdictionKey | null) => {
    setCity(option);
  }, []);

  const handleIssueDescription = useCallback(
    (event: React.ChangeEvent<HTMLTextAreaElement>) => {
      setIssueDescription(
        DOMPurify.sanitize(event.target.value, SANITIZE_USER_SETTINGS),
      );
    },
    [],
  );

  // Location is owned by the navbar picker / URL, so a form reset leaves it.
  const handleFormReset = useCallback(() => {
    setIssueDescription("");
  }, []);

  const housingContextObject = useMemo(
    () => ({
      housingLocation,
      city,
      issueDescription,
      handleHousingLocation,
      handleCityChange,
      handleIssueDescription,
      handleFormReset,
    }),
    [
      housingLocation,
      city,
      issueDescription,
      handleHousingLocation,
      handleCityChange,
      handleIssueDescription,
      handleFormReset,
    ],
  );

  return (
    <HousingContext.Provider value={housingContextObject}>
      {children}
    </HousingContext.Provider>
  );
}

export { HousingContext };
