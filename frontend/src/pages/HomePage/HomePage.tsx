import BeaverIcon from "../../shared/components/BeaverIcon";
import TenantFirstAidLogo from "../../shared/components/TenantFirstAidLogo";
import brainyFeatures from "./BrainyFeatures";
import { REFERENCED_LAW_LIST } from "../../shared/constants/constants";
import HPFeedbackForm from "./HPFeedBackForm/HPFeedbackForm";
import AirVentIcon from "../../shared/components/AirVentIcon";
import ChartIcon from "../../shared/components/ChartIcon";
import ActivityIcon from "../../shared/components/ActivityIcon";
import ComparisonGrid from "./ComparisonGrid/ComparisonGrid";
import clsx from "clsx";
import LetterCarousel from "./LetterCarousel/LetterCarousel";
const HomePage = () => {

  return (
    <>
      <div
        className="bg-emerald-950 w-full overflow-x-hidden relative text-[#F4F4F2] selection:bg-emerald-500 selection:text-white"
      >
        <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[150vw] h-auto opacity-5 z-0 pointer-events-none flex items-center justify-center text-emerald-500">
          <TenantFirstAidLogo />
        </div>

        <div className="fixed left-0 top-0 w-3 h-screen bg-emerald-900 z-1 opacity-80 border-r border-[#E6D5B8] pointer-events-none max-[950px]:hidden"></div>
        <div className="fixed right-0 top-0 w-3 h-screen bg-emerald-900 z-1 opacity-80 border-l border-[#E6D5B8] pointer-events-none max-[950px]:hidden"></div>

        <section className="min-h-[56vh] flex items-center justify-center py-10 px-5 relative z-2">
          <div className="p-3.5 backdrop-blur-lg w-[425px] shadow-[0_8px_32px_rgba(0,0,0,0.2)] rounded-3xl">
            <div className="flex items-center justify-center gap-[7.5px] flex-wrap">
              <div className="w-[90px] h-[90px] flex items-center">
                <BeaverIcon />
              </div>
              <h1 className="text-[32px] max-[950px]:text-[2.5rem] m-0 font-black text-[#F4F4F2] drop-shadow-none">
                Tenant First Aid
              </h1>
            </div>
            <p className="mt-[25px] text-[#F4F4F2] text-base leading-[1.8] font-medium"></p>
          </div>
        </section>

        <div className="w-full bg-[#E6D5B8]/10 backdrop-blur-lg relative z-2 py-16 border-y border-[#E6D5B8]/20">
          <div className="text-white flex justify-center gap-[60px] max-w-[1200px] mx-auto max-[950px]:flex-col">
            <div className="flex-1 text-center">
              <div className="cursor-pointer mt-5 text-emerald-500 font-semibold">
                <a href="/chat" className="no-underline">
                  <h4 className="text-[32px] text-[#F4F4F2] border-b-2 border-emerald-500 pb-[15px] font-bold">
                    Chat with Brainy<span className="pl-2.5">→</span>
                  </h4>
                </a>
              </div>
            </div>
            <div className="flex-1 text-center">
              <div className="cursor-pointer mt-5 text-emerald-500 font-semibold">
                <a href="/letter" className="no-underline">
                  <h4 className="text-[32px] text-[#F4F4F2] border-b-2 border-emerald-500 pb-[15px] font-bold">
                    Draft a letter<span className="pl-2.5">→</span>
                  </h4>
                </a>
              </div>
            </div>
          </div>
        </div>

        <section className="max-w-[1200px] my-20 mx-auto px-5 relative z-2">
          <div className="flex gap-[100px] items-start max-[950px]:flex-col-reverse max-[950px]:gap-20">
            <div className="flex-1">
              <h3 className="text-[32px] mb-10 text-[#F4F4F2] font-extrabold">
                How to use Brainy
              </h3>
              <div className="flex flex-col">
                {brainyFeatures.map((item, i) => (
                  <div key={item.id} className={clsx("flex gap-[30px]")}>
                    <div
                      className={clsx("flex flex-col items-center w-[30px]")}
                    >
                      <div
                        className={clsx(
                          "w-5 h-5 rounded-full border-2 z-2",
                          "bg-emerald-500 border-emerald-900",
                        )}
                      ></div>

                      {i === 0 && (
                        <div className={clsx("w-0.5 flex-1 bg-white/20")}></div>
                      )}
                    </div>

                    <div className={clsx("flex-1 pb-10")}>
                      <h4
                        className={clsx("text-[1.6rem] my-2", "text-[#F4F4F2]")}
                      >
                        {item.title}
                      </h4>

                      <p
                        className={clsx(
                          "leading-[1.6] opacity-90",
                          "text-[#F4F4F2]",
                        )}
                      >
                        {item.desc}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Carousel Column */}
            <div className="flex-[1.5] relative max-[950px]:pr-0 max-[950px]:mt-[60px] max-[950px]:w-[100vw] max-[950px]:-ml-5">
              <LetterCarousel />

              <p className="text-center text-emerald-500 mt-9 text-base italic font-bold w-full block">
                Example outputs generated by Brainy
              </p>
            </div>
          </div>
        </section>

        <section
          id="how-it-works"
          className="max-w-[1200px] my-20 mx-auto px-5 relative z-2"
        >
          <div className="w-full">
            <h2 className="text-center mb-5 text-[#F4F4F2] text-4xl font-extrabold">
              Why ask Brainy?
            </h2>
            <p className="text-center mt-2.5 mb-[50px] text-[1.4rem] text-emerald-400 font-semibold">
              Brainy uses a{" "}
              <span className="text-[#E6D5B8] font-bold underline decoration-emerald-500">
                Retrieval-Augmented Generation
              </span>{" "}
              approach to look up information from curated legal sources
            </p>
            <div className="flex gap-10 mt-[50px] max-[950px]:flex-col">
              <div className="flex-1 bg-[#E6D5B8]/10 backdrop-blur-lg p-8 border border-[#E6D5B8]/20 rounded-3xl shadow-[0_10px_25px_rgba(0,0,0,0.2)]">
                <h4 className="text-[1.3rem] font-bold mb-4 flex items-center gap-4 text-[#F4F4F2]">
                  <AirVentIcon size={24} color="#10B981" /> Retrieve
                </h4>
                <p className="text-base text-[#F4F4F2] leading-[1.6]">
                  Brainy retrieves the most relevant information about Oregon
                  housing law, including
                </p>
                <ul className="list-disc pl-4">
                  {Object.entries(REFERENCED_LAW_LIST).map(
                    ([key, reference]) => (
                      <li key={key}>
                        <a
                          href={reference.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-link hover:text-blue-dark"
                        >
                          {reference.label}
                        </a>
                      </li>
                    ),
                  )}
                </ul>
              </div>
              <div className="flex-1 bg-[#E6D5B8]/10 backdrop-blur-lg p-8 border border-[#E6D5B8]/20 rounded-3xl shadow-[0_10px_25px_rgba(0,0,0,0.2)]">
                <h4 className="text-[1.3rem] font-bold mb-4 flex items-center gap-4 text-[#F4F4F2]">
                  <ChartIcon size={24} color="#10B981" /> Augment
                </h4>
                <p className="text-base text-[#F4F4F2] leading-[1.6]">
                  Brainy combines what it finds with the questions the user
                  asks.
                </p>
              </div>
              <div className="flex-1 bg-[#E6D5B8]/10 backdrop-blur-lg p-8 border border-[#E6D5B8]/20 rounded-3xl shadow-[0_10px_25px_rgba(0,0,0,0.2)]">
                <h4 className="text-[1.3rem] font-bold mb-4 flex items-center gap-4 text-[#F4F4F2]">
                  <ActivityIcon size={24} color="#10B981" /> Generate
                </h4>
                <p className="text-base text-[#F4F4F2] leading-[1.6]">
                  Brainy writes a clear, concise answer.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section
          id="compare"
          className="max-w-[1100px] my-20 mx-auto px-5 relative z-2 max-[550px]:px-0"
        >
          <h2 className="text-center px-[10vw] mb-5 text-[#F4F4F2] text-4xl font-extrabold">
            Which approach is right for you?
          </h2>
          <ComparisonGrid />
        </section>

        <section className="max-w-[1200px] my-20 mx-auto px-5 relative z-2 text-center mb-20">
          <div>
            <a
              href="/privacy-policy"
              className="text-emerald-500 text-[1.2rem] underline cursor-pointer font-bold"
            >
              Privacy Policy
            </a>
            <p className="mt-[15px] text-[#F4F4F2] opacity-80 text-base">
              We don't store any of the information you input either in the
              session or on any servers
            </p>
          </div>
        </section>

        <section className="max-w-[1200px] my-20 mx-auto px-5 relative z-2 text-center mb-20">
          <div>
            <a
              href="/disclaimer"
              className="text-emerald-500 text-[1.2rem] underline cursor-pointer font-bold"
            >
              Disclaimer
            </a>
            <p className="text-[#F4F4F2] opacity-80 text-base max-w-[800px] mx-auto leading-[1.6]">
              The information provided by this chatbot is general information
              only and does not constitute legal advice. While Tenant First Aid
              strives to keep the content accurate and up to date, completeness
              and accuracy is not guaranteed. If you have a specific legal issue
              or question, consider contacting a qualified attorney or a local
              legal aid clinic for personalized assistance. For questions
              related to Tenant First Aid, contact{" "}
              <a
                href="mailto:michael@qiu-qiulaw.com"
                className="text-emerald-500"
              >
                michael@qiu-qiulaw.com
              </a>
              .
            </p>
          </div>
        </section>

        <section className="max-w-[1200px] my-20 mx-auto px-5 relative z-2">
          <div className="p-16 bg-[#E6D5B8]/10 backdrop-blur-lg border border-[#E6D5B8]/20 text-center rounded-3xl shadow-[0_15px_40px_rgba(0,0,0,0.2)]">
            <h2 className="text-4xl font-extrabold text-[#F4F4F2] mb-5">
              Who We Are
            </h2>
            <p className="text-[1.3rem] leading-[1.9] text-[#F4F4F2] font-normal">
              <strong>Tenant First Aid</strong> is a volunteer-built program by{" "}
              <a href="https://www.codepdx.org/" className="text-emerald-500">
                Code PDX
              </a>{" "}
              and{" "}
              <a
                href="mailto:michael@qiu-qiulaw.com"
                className="text-emerald-500"
              >
                Qiu Qiu Law
              </a>
              .
            </p>
          </div>
        </section>

        <section className="h-[16vh] flex items-center justify-center relative overflow-hidden">
          <div className="text-center z-3">
            <h1 className="text-[clamp(2.6rem,10vw,2.6rem)] font-black text-[#F4F4F2]">
              Get in touch
            </h1>
          </div>
        </section>

        <HPFeedbackForm />
      </div>
    </>
  );
};

export default HomePage;
