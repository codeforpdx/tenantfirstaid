import { createContext, useCallback, useMemo, useState } from "react";
import DOMPurify, { SANITIZE_USER_SETTINGS } from "../shared/utils/dompurify";
import type { ILocation } from "../types/HousingTypes";
import type {
  TCitySelectKey,
  THousingType,
  TTenantTopic,
} from "../shared/constants/constants";

export interface IHousingContextType {
  housingLocation: ILocation;
  city: TCitySelectKey | null;
  housingType: THousingType | null;
  tenantTopic: TTenantTopic | null;
  issueDescription: string;
  handleHousingLocation: ({ city, state }: ILocation) => void;
  handleCityChange: (option: TCitySelectKey | null) => void;
  handleHousingChange: (option: THousingType | null) => void;
  handleTenantTopic: (option: TTenantTopic | null) => void;
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
  const [city, setCity] = useState<TCitySelectKey | null>(null);
  const [housingLocation, setHousingLocation] = useState<ILocation>({
    city: null,
    state: null,
  });
  const [housingType, setHousingType] = useState<THousingType | null>(null);
  const [tenantTopic, setTenantTopic] = useState<TTenantTopic | null>(null);
  const [issueDescription, setIssueDescription] = useState("");

  const handleHousingLocation = useCallback(({ city, state }: ILocation) => {
    setHousingLocation({ city, state });
  }, []);

  const handleCityChange = useCallback((option: TCitySelectKey | null) => {
    setCity(option);
  }, []);

  const handleHousingChange = useCallback((option: THousingType | null) => {
    setHousingType(option);
  }, []);

  const handleTenantTopic = useCallback((option: TTenantTopic | null) => {
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
