//Headers for the comparison grid
const headers = ["", "Tenant First Aid", "Traditional Legal Aid", "ChatGPT"];

// 2. Extract table data into a clean structure
const comparisonData = [
  {
    feature: "Always available",
    tenantFirstAid: true,
    traditional: false,
    chatgpt: true,
  },
  {
    feature: "Always free",
    tenantFirstAid: true,
    traditional: false,
    chatgpt: false,
  },
  {
    feature: "No eligibility requirements",
    tenantFirstAid: true,
    traditional: false,
    chatgpt: true,
  },
  {
    feature: "Provides legal advice",
    tenantFirstAid: false,
    traditional: true,
    chatgpt: false,
  },
  {
    feature: "Only references relevant laws",
    tenantFirstAid: true,
    traditional: true,
    chatgpt: false,
  },
  {
    feature: "Direct advocacy with court/landlords",
    tenantFirstAid: false,
    traditional: true,
    chatgpt: false,
  },
];

export { headers, comparisonData };
