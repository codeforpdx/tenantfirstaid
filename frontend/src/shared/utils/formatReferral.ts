import type {
  CaseStage,
  GeographicScope,
  HoursBlock,
  ProviderType,
  ServiceType,
  Weekday,
} from "../../types/models";

const SERVICE_TYPE_LABELS: Record<ServiceType, string> = {
  legal_representation: "Legal Representation",
  answer_questions: "Answer Questions",
};

const PROVIDER_TYPE_LABELS: Record<ProviderType, string> = {
  attorney: "Attorney",
  licensed_paralegal: "Licensed Paralegal",
  non_attorney: "Non-Attorney",
};

const WEEKDAY_LABELS: Record<Weekday, string> = {
  monday: "Mon",
  tuesday: "Tue",
  wednesday: "Wed",
  thursday: "Thu",
  friday: "Fri",
  saturday: "Sat",
  sunday: "Sun",
};

export function formatServiceTypes(serviceTypes: ServiceType[]): string {
  return serviceTypes.map((s) => SERVICE_TYPE_LABELS[s]).join(", ");
}

export function formatProviderTypes(providerTypes: ProviderType[]): string {
  return providerTypes.map((p) => PROVIDER_TYPE_LABELS[p]).join(", ");
}

/** Describes when a tenant can use this service relative to an eviction filing. */
export function formatCaseStages(caseStages: CaseStage[]): string | null {
  const beforeCourt = caseStages.includes("before_court");
  const inCourt = caseStages.includes("in_court");
  if (beforeCourt && inCourt) return "Any stage";
  if (inCourt) return "After eviction filed";
  if (beforeCourt) return "Before eviction filed";
  return null;
}

export function formatGeographicScope(scope: GeographicScope): string {
  if (!scope.cities || scope.cities.length === 0) return "All of Oregon";
  return (
    scope.cities
      .map((city) => city.charAt(0).toUpperCase() + city.slice(1))
      .join(", ") + " only"
  );
}

function formatTime(time: string): string {
  const [hourStr, minuteStr] = time.split(":");
  const hour = parseInt(hourStr, 10);
  const period = hour < 12 ? "am" : "pm";
  const hour12 = hour % 12 === 0 ? 12 : hour % 12;
  const minutes = minuteStr && minuteStr !== "00" ? `:${minuteStr}` : "";
  return `${hour12}${minutes}${period}`;
}

export function formatHoursBlock(block: HoursBlock): string {
  const days = block.days.map((day) => WEEKDAY_LABELS[day]).join(", ");
  return `${days} ${formatTime(block.start)}–${formatTime(block.end)}`;
}
