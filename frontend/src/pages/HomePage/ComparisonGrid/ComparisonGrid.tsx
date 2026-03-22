import React from "react";
import CheckCircle from "../../../shared/components/CheckCircleIcon";
import XCircle from "../../../shared/components/XCircleIcon";
import { headers, comparisonData } from "./ComparisonData";

const ComparisonGrid = () => {
  const renderIcon = (hasFeature: boolean) =>
    hasFeature ? <CheckCircle /> : <XCircle />;

  return (
    <div className="bg-[#E6D5B8]/10 backdrop-blur-lg border border-[#E6D5B8]/20 p-12 shadow-[0_15px_40px_rgba(0,0,0,0.2)] rounded-3xl overflow-hidden max-[950px]:overflow-x-auto max-[950px]:p-6 max-[950px]:pl-0">
      <div className="grid grid-cols-4 gap-px bg-[#E6D5B8]/10 max-[950px]:min-w-[700px] [&>div:nth-child(4n+1)]:max-[950px]:sticky [&>div:nth-child(4n+1)]:max-[950px]:left-0 [&>div:nth-child(4n+1)]:max-[950px]:z-10 [&>div:nth-child(4n+1)]:max-[950px]:border-r [&>div:nth-child(4n+1)]:max-[950px]:border-[#E6D5B8]/20 [&>div:nth-child(4n+1)]:max-[950px]:bg-[#0E362D] [&>div:nth-child(1)]:max-[950px]:!bg-emerald-900">
        {/* Render Headers */}
        {headers.map((header, idx) => (
          <div
            key={`header-${idx}`}
            className="p-5 font-bold bg-emerald-900/80 text-[#F4F4F2] text-center"
          >
            {header}
          </div>
        ))}

        {/* Render Data Rows */}
        {comparisonData.map((row, idx) => (
          // React.Fragment is crucial here so we don't break CSS Grid and nth-child selectors
          <React.Fragment key={`row-${idx}`}>
            {/* Feature Name (Sticky Column) */}
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium">
              {row.feature}
            </div>

            {/* Tenant First Aid Column */}
            <div className="p-5 bg-[#E6D5B8]/5 text-center font-bold flex items-center justify-center">
              {renderIcon(row.tenantFirstAid)}
            </div>

            {/* Traditional Legal Aid Column */}
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium">
              {renderIcon(row.traditional)}
            </div>

            {/* ChatGPT Column */}
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium">
              {renderIcon(row.chatgpt)}
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default ComparisonGrid;
