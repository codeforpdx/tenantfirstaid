import { createContext, useCallback, useMemo, useState } from "react";
import DOMPurify, { SANITIZE_USER_SETTINGS } from "../shared/utils/dompurify";

export interface ILocation {
  city: string | null;
  state: string | null;
}

export interface IHousingContextType {
  housingLocation: ILocation;
  city: string | null;
  housingType: string | null;
  tenantTopic: string | null;
  issueDescription: string;
  handleHousingLocation: ({ city, state }: ILocation) => void;
  handleCityChange: (option: string | null) => void;
  handleHousingChange: (option: string | null) => void;
  handleTenantTopic: (option: string | null) => void;
  handleIssueDescription: (
    event: React.ChangeEvent<HTMLTextAreaElement>,
  ) => void;
  handleFormReset: () => void;
}

const HousingContext = createContext<IHousingContextType | null>(null);

interface Props {
  children: React.ReactNode;
}

export default function HousingContextProvider({ children }: Props) {
  const [city, setCity] = useState<string | null>(null);
  const [housingLocation, setHousingLocation] = useState<ILocation>({
    city: null,
    state: null,
  });
  const [housingType, setHousingType] = useState<string | null>(null);
  const [tenantTopic, setTenantTopic] = useState<string | null>(null);
  const [issueDescription, setIssueDescription] = useState("");

  const handleHousingLocation = useCallback(({ city, state }: ILocation) => {
    setHousingLocation({ city, state });
  }, []);

  const handleCityChange = useCallback((option: string | null) => {
    setCity(option);
  }, []);

  const handleHousingChange = useCallback((option: string | null) => {
    setHousingType(option);
  }, []);

  const handleTenantTopic = useCallback((option: string | null) => {
    setTenantTopic(option);
  }, []);

  const handleIssueDescription = useCallback(
    (event: React.ChangeEvent<HTMLTextAreaElement>) => {
      setIssueDescription(
        DOMPurify.sanitize(event.target.value, SANITIZE_USER_SETTINGS),
      );
    },
    [],
  );

  const handleFormReset = useCallback(() => {
    setCity(null);
    setHousingLocation({ city: null, state: null });
    setHousingType(null);
    setTenantTopic(null);
    setIssueDescription("");
  }, []);

  const housingContextObject = useMemo(
    () => ({
      housingLocation,
      city,
      housingType,
      tenantTopic,
      issueDescription,
      handleHousingLocation,
      handleCityChange,
      handleHousingChange,
      handleTenantTopic,
      handleIssueDescription,
      handleFormReset,
    }),
    [
      housingLocation,
      city,
      housingType,
      tenantTopic,
      issueDescription,
      handleHousingLocation,
      handleCityChange,
      handleHousingChange,
      handleTenantTopic,
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
