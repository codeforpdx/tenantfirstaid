import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReferralList } from "../../types/models";
import useReferrals from "../../hooks/useReferrals";
import Referrals from "../../Referrals";

vi.mock("../../hooks/useReferrals", () => ({
  default: vi.fn(),
}));

const referrals: ReferralList = [
  {
    id: "clear-clinic",
    organization: "CLEAR Clinic",
    service_types: ["answer_questions"],
    provider_types: ["attorney", "licensed_paralegal"],
    geographic_scope: { state: "or", cities: [] },
    eligibility: [],
    case_stages: ["before_court", "in_court"],
    hours: [{ days: ["tuesday", "thursday"], start: "09:00", end: "17:00" }],
    phone: "503-389-5919",
    email: "info@clear-clinic.org",
    website: "https://clear-clinic.org/services",
    notes: null,
  },
  {
    id: "commons-law-center",
    organization: "Commons Law Center",
    service_types: ["legal_representation"],
    provider_types: ["attorney"],
    geographic_scope: { state: "or", cities: ["portland"] },
    eligibility: ["Must already have a court date"],
    case_stages: ["in_court"],
    hours: [
      {
        days: ["monday", "tuesday", "thursday"],
        start: "08:00",
        end: "12:00",
      },
    ],
    phone: null,
    email: null,
    website: null,
    notes: "No appointment needed.",
  },
];

function mockUseReferrals(value: {
  data?: ReferralList;
  isLoading: boolean;
  isError: boolean;
}) {
  vi.mocked(useReferrals).mockReturnValue(
    value as ReturnType<typeof useReferrals>,
  );
}

describe("Referrals", () => {
  beforeEach(() => {
    vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state", () => {
    mockUseReferrals({ isLoading: true, isError: false });

    render(<Referrals />);

    expect(screen.getByText("Loading referrals...")).toBeInTheDocument();
  });

  it("shows an error state", () => {
    mockUseReferrals({ isLoading: false, isError: true });

    render(<Referrals />);

    expect(
      screen.getByText(
        "Unable to load referrals right now. Please try again later.",
      ),
    ).toBeInTheDocument();
  });

  it("renders referral rows from the hook data", () => {
    mockUseReferrals({ data: referrals, isLoading: false, isError: false });

    render(<Referrals />);

    expect(
      screen.getByRole("heading", { name: "Referrals" }),
    ).toBeInTheDocument();
    expect(screen.getByText("CLEAR Clinic")).toBeInTheDocument();
    expect(screen.getByText("Answer Questions")).toBeInTheDocument();
    expect(
      screen.getByText("Attorney, Licensed Paralegal"),
    ).toBeInTheDocument();
    expect(screen.getByText("Any stage")).toBeInTheDocument();
    expect(screen.getByText("All of Oregon")).toBeInTheDocument();
    expect(screen.getByText("Tue, Thu 9am–5pm")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "info@clear-clinic.org" }),
    ).toHaveAttribute("href", "mailto:info@clear-clinic.org");
    expect(
      screen.getByRole("link", { name: "https://clear-clinic.org/services" }),
    ).toHaveAttribute("href", "https://clear-clinic.org/services");
    expect(screen.getByText("Commons Law Center")).toBeInTheDocument();
    expect(screen.getByText("Portland only")).toBeInTheDocument();
    expect(
      screen.getByText("Must already have a court date"),
    ).toBeInTheDocument();
    expect(screen.getByText("No appointment needed.")).toBeInTheDocument();
  });
});
