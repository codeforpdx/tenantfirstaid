import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router";
import useHousingContext from "./useHousingContext";
import {
  JURISDICTION_OPTIONS,
  type JurisdictionOption,
} from "../shared/constants/jurisdictions";
import {
  pathFor,
  jurisdictionByKey,
  jurisdictionFromPathname,
  toLocation,
} from "../shared/utils/jurisdiction";

/**
 * Exposes the active jurisdiction and a `selectLocation` action used by the
 * navbar/sidebar location picker. On chat/letter the URL is the source of
 * truth; elsewhere (e.g. the homepage) there is no jurisdiction in the URL, so
 * it falls back to the picked location, defaulting to Oregon at large.
 * Selecting a location keeps the user on their current feature by navigating
 * within it.
 */
export default function useActiveJurisdiction() {
  const { city, handleCityChange, handleHousingLocation } = useHousingContext();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const isFeaturePath =
    pathname.startsWith("/chat") || pathname.startsWith("/letter");
  const active = isFeaturePath
    ? jurisdictionFromPathname(pathname)
    : jurisdictionByKey(city);

  const selectLocation = useCallback(
    (option: JurisdictionOption) => {
      handleCityChange(option.key);
      handleHousingLocation(toLocation(option));
      if (pathname.startsWith("/letter")) {
        navigate(pathFor("letter", option));
      } else if (pathname.startsWith("/chat")) {
        navigate(pathFor("chat", option));
      }
    },
    [handleCityChange, handleHousingLocation, navigate, pathname],
  );

  return { active, options: JURISDICTION_OPTIONS, selectLocation };
}
