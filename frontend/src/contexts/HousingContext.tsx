import { createContext, useCallback, useMemo, useState } from "react";
import DOMPurify, { SANITIZE_USER_SETTINGS } from "../shared/utils/dompurify";
import type { Location } from "../types/models";
import type {
  CitySelectKey,
  HousingType,
  TenantTopic,
} from "../shared/constants/constants";

export interface HousingContextType {
  housingLocation: Location;
  city: CitySelectKey | null;
  housingType: HousingType | null;
  tenantTopic: TenantTopic | null;
  issueDescription: string;
  handleHousingLocation: ({ city, state }: Location) => void;
  handleCityChange: (option: CitySelectKey | null) => void;
  handleHousingChange: (option: HousingType | null) => void;
  handleTenantTopic: (option: TenantTopic | null) => void;
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
  const [city, setCity] = useState<CitySelectKey | null>(null);
  const [housingLocation, setHousingLocation] = useState<Location>({
    city: null,
    state: null,
  });
  const [housingType, setHousingType] = useState<HousingType | null>(null);
  const [tenantTopic, setTenantTopic] = useState<TenantTopic | null>(null);
  const [issueDescription, setIssueDescription] = useState("");

  const handleHousingLocation = useCallback(({ city, state }: Location) => {
    setHousingLocation({ city, state });
  }, []);

  const handleCityChange = useCallback((option: CitySelectKey | null) => {
    setCity(option);
  }, []);

  const handleHousingChange = useCallback((option: HousingType | null) => {
    setHousingType(option);
  }, []);

  const handleTenantTopic = useCallback((option: TenantTopic | null) => {
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
