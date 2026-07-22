import { useEffect } from "react";
import { scrollToTop } from "./shared/utils/scrolling";
import referrals from "./generated/referrals";
import SafeMarkdown from "./shared/components/SafeMarkdown";
import {
  formatCaseStages,
  formatGeographicScope,
  formatHoursBlock,
  formatProviderTypes,
  formatServiceTypes,
} from "./shared/utils/formatReferral";

export default function Referrals() {
  useEffect(() => {
    scrollToTop();
  }, []);

  return (
    <div className="w-full px-4 py-6">
      <h2 className="text-2xl font-bold mb-6 text-center">Referrals</h2>

      <div className="overflow-x-auto">
        <table className="w-[1100px] table-fixed border-collapse text-sm text-gray-dark rounded overflow-hidden mx-auto">
          <thead>
            <tr className="bg-green-light/40">
              <th className="w-[180px] border border-gray-medium px-4 py-3 text-left font-semibold">
                Organization
              </th>
              <th className="w-[270px] border border-gray-medium px-4 py-3 text-left font-semibold">
                Service
              </th>
              <th className="w-[150px] border border-gray-medium px-4 py-3 text-center font-semibold">
                Locations
              </th>
              <th className="w-[500px] border border-gray-medium px-4 py-3 text-left font-semibold">
                Availability / Contact
              </th>
            </tr>
          </thead>
          <tbody>
            {referrals.map((referral) => {
              const caseStageLabel = formatCaseStages(
                referral.case_stages ?? [],
              );
              return (
                <tr key={referral.id} className="bg-white">
                  <td className="border border-gray-medium px-4 py-3 font-semibold align-top">
                    {referral.organization}
                  </td>
                  <td className="border border-gray-medium px-4 py-3 align-top">
                    <div>{formatServiceTypes(referral.service_types)}</div>
                    {referral.provider_types &&
                      referral.provider_types.length > 0 && (
                        <div className="text-gray-medium">
                          {formatProviderTypes(referral.provider_types)}
                        </div>
                      )}
                    {caseStageLabel && (
                      <div className="text-gray-medium">{caseStageLabel}</div>
                    )}
                  </td>
                  <td className="border border-gray-medium px-4 py-3 text-center align-top">
                    {formatGeographicScope(referral.geographic_scope)}
                  </td>
                  <td className="border border-gray-medium px-4 py-3 align-top">
                    {referral.hours &&
                      referral.hours.length > 0 &&
                      referral.hours.map((block, i) => (
                        <div key={i}>{formatHoursBlock(block)}</div>
                      ))}
                    {referral.phone && <div>{referral.phone}</div>}
                    {referral.email && (
                      <div>
                        Email:{" "}
                        <a
                          href={`mailto:${referral.email}`}
                          className="text-blue-600 underline"
                        >
                          {referral.email}
                        </a>
                      </div>
                    )}
                    {referral.website && (
                      <div>
                        Website:{" "}
                        <a
                          href={referral.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 underline"
                        >
                          {referral.website}
                        </a>
                      </div>
                    )}
                    {referral.eligibility &&
                      referral.eligibility.length > 0 && (
                        <div>{referral.eligibility.join("; ")}</div>
                      )}
                    {referral.notes && (
                      <div className="mt-1">
                        <SafeMarkdown>{referral.notes}</SafeMarkdown>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
