import { createContext, useContext } from "react";

export type DevicePrivacy = "private" | "public";

export const DevicePrivacyContext = createContext<DevicePrivacy | null>(null);

export function useDevicePrivacy() {
  return useContext(DevicePrivacyContext);
}
