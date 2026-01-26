const CONTACT_EMAIL = "michael@qiu-qiulaw.com";

interface CitySelectOptionType {
  city: string | null;
  state: string | null;
  label: string;
}

const CITY_SELECT_OPTIONS: Record<string, CitySelectOptionType> = {
  portland: {
    city: "Portland",
    state: "OR",
    label: "Portland",
  },
  eugene: {
    city: "Eugene",
    state: "OR",
    label: "Eugene",
  },
  oregon: {
    city: null,
    state: "OR",
    label: "Other city in Oregon",
  },
  other: {
    city: null,
    state: null,
    label: "City in another state",
  },
};

const HOUSING_OPTIONS = [
  "Apartment/House Rental",
  "Manufactured/Mobile Home",
  "RV/Tiny Home (on wheels)",
  "Room Rental/Shared Housing",
  "Other",
];

const LETTERABLE_TOPIC_OPTIONS = {
  "Repairs and Conditions": {
    example: [
      "What can I do about my broken heater?",
      "Should me or my landlord pay for repairs?",
      "Is _ something that my landlord has to fix?",
    ],
    label: "Repairs and Conditions",
  },
  "Security Deposits and Fees": {
    example: [
      "What is the maximum amount that my landlord can request for a security deposit?",
      "My landlord is refusing to return my security deposit, what can I do?",
      "Are fees for _ allowed?",
    ],
    label: "Security Deposits and Fees",
  },
  "Rent Issues": {
    example: [
      "My landlord increased my rent, is this allowed?",
      "I fell behind on rent, what should I do?",
      "Charges for _ utility service are included in my rent. Is this allowed?",
    ],
    label: "Rent Issues",
  },
  "Entry and Privacy": {
    example: [
      "Can my landlord enter my unit without telling me?",
      "My neighbors are disrupting me with _. What can I do?",
    ],
    label: "Entry and Privacy",
  },
  "Discrimination/Fair Housing": {
    example: [
      "I am being treated unfairly because of my _ (e.g., race, gender). What should I do?",
      "I don't think my application to rent an apartment was treated fairly. What are my rights?",
      "Can landlords ask about _ on rental applications?",
    ],
    label: "Discrimination/Fair Housing",
  },
  "Lease/Rental Agreement": {
    example: [
      "What does _(e.g., subordination) mean in my lease?",
      "I don't have a written rental agreement, do I still have tenant rights?",
      "Can my lease agreement legally require me to _ ?",
      "I want to end my lease and move out. What should I do?",
    ],
    label: "Lease/Rental Agreement",
  },
  "Manufacture Home Park Issues": {
    example: [
      "Can my landlord end my space lease because of the appearance of my mobile home?",
      "I heard that my landlord wants to close the park where I live. What are my rights?",
      "I want to sell my manufactured home and move out. What should I do?",
    ],
    label: "Manufacture Home Park Issues",
  },
};

const NONLETTERABLE_TOPIC_OPTIONS = {
  "Eviction and Notices": {
    example: [
      "Do I have to move if my landlord asks me to move out?",
      "I received an eviction notice, what should I do?",
      "Can I be evicted for _?",
    ],
    label: "Eviction and Notices",
  },
  Other: {
    example: [
      "My landlord told me they are going to sell my building. What are my rights?",
      "I want to have a roommate move-in with me. What should I do?",
      "Can I sublease my apartment or rent it to some else?",
    ],
    label: "Other",
  },
};

const ALL_TOPIC_OPTIONS = {
  ...LETTERABLE_TOPIC_OPTIONS,
  ...NONLETTERABLE_TOPIC_OPTIONS,
};

const REFERENCED_LAW_LIST = {
  "ORS 90": {
    link: "https://www.oregonlegislature.gov/bills_laws/ors/ors090.html",
    label: "ORS 90 (as amended 2023)",
  },
  "ORS 105": {
    link: "https://www.oregonlegislature.gov/bills_laws/ors/ors105.html",
    label: "ORS 105",
  },
  "Section 8.425": {
    link: "https://eugene.municipal.codes/EC/8.425",
    label: "Eugene Code Section 8.425",
  },
  "City Code Title 30": {
    link: "https://www.portland.gov/code/30/all",
    label: "Portland City Code Title 30",
  },
};

const NAVBAR_LINKS = [
  { to: "/", label: "Chat" },
  { to: "/letter", label: "Letter" },
  { to: "/about", label: "About Tenant First Aid" },
  { to: "/disclaimer", label: "Disclaimer" },
  { to: "/privacy-policy", label: "Privacy Policy" },
];

export {
  CITY_SELECT_OPTIONS,
  HOUSING_OPTIONS,
  LETTERABLE_TOPIC_OPTIONS,
  NONLETTERABLE_TOPIC_OPTIONS,
  ALL_TOPIC_OPTIONS,
  CONTACT_EMAIL,
  REFERENCED_LAW_LIST,
  NAVBAR_LINKS,
};

export type { CitySelectOptionType };
