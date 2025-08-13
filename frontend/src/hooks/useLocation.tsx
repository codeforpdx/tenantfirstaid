import { useEffect, useState } from "react";

export interface ILocation {
  city: string | null;
  state: string | null;
}

export default function useLocation() {
  const [location, setLocation] = useState<ILocation>({
    city: null,
    state: null,
  });

  useEffect(() => {
    // Initialize location if needed
    if (!location.city && !location.state) {
      setLocation({ city: null, state: null });
    }
  }, [location.city, location.state]);

  return { location, setLocation };
}
