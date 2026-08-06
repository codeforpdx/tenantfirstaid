import { useEffect } from "react";
import { useParams } from "react-router";
import useHousingContext from "./useHousingContext";
import { resolveJurisdiction, toLocation } from "../shared/utils/jurisdiction";

/**
 * Seeds HousingContext from the URL :state/:city params so the URL is the
 * source of truth for the selected jurisdiction.
 */
export default function useSyncJurisdiction() {
  const { state, city } = useParams();
  const { handleHousingLocation, handleCityChange } = useHousingContext();

  useEffect(() => {
    const jurisdiction = resolveJurisdiction(state, city);
    handleHousingLocation(toLocation(jurisdiction));
    handleCityChange(jurisdiction.key);
  }, [state, city, handleHousingLocation, handleCityChange]);
}
