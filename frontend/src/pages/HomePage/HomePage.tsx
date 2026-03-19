import React, { useRef, useState } from 'react';
import BeaverIcon from '../../shared/components/BeaverIcon';
import TenantFirstAidLogo from "../../shared/components/TenantFirstAidLogo";
import LetterTemplate from '../../../public/LetterTemplate.png';
import ChatExample from '../../../public/ChatExample.png';
import LetterExample from '../../../public/LetterExample.png';
import { REFERENCED_LAW_LIST } from '../../shared/constants/constants';
import HPFeedbackForm from './HPFeedbackForm';
import AirVentIcon from '../../shared/components/AirVentIcon';
import ChartIcon from '../../shared/components/ChartIcon';
import ActivityIcon from '../../shared/components/ActivityIcon';
import CheckCircle from '../../shared/components/CheckCircleIcon';
import XCircle from '../../shared/components/XCircleIcon';
import ChevronRight from '../../shared/components/ChevronRight';
import clsx from 'clsx';

const HomePage = () => {
  const mainRef = useRef(null);
  const [activeLetterIndex, setActiveLetterIndex] = useState(0);
  const letterImages = [{src :LetterTemplate, id : "LetterTemplate"}, {src :ChatExample, id : "ChatExample"}, {src :LetterExample, id : "LetterExample"}];

  const handleNextLetter = () => {
    setActiveLetterIndex((prev) => (prev + 1) % letterImages.length);
  };

  const roadmapItems = [
    {title: "Ask questions", desc: "Chat with Brainy about your housing issues.", status: "complete", id: "chat"},
    {title: "Write letters", desc: "Brainy can help draft letters to your landlord.", status: "active", id: "letter"},
  ];

  // --- HELPER FUNCTIONS ---
  const getCardStyle = (index: number) => {
    const position = (index - activeLetterIndex + letterImages.length) % letterImages.length;
    
    if (position === 0) {
      return { zIndex: 10, transform: 'scale(1) translateX(0) translateY(0) rotate(0deg)', opacity: 1 };
    } else if (position === 1) {
      return { zIndex: 9, transform: 'scale(0.98) translateX(-20px) translateY(-25px) rotate(-2deg)', opacity: 0.8 };
    } else {
      return { zIndex: 8, transform: 'scale(0.96) translateX(-40px) translateY(-50px) rotate(-4deg)', opacity: 0.6 };
    }
  };

  return (
    <>
    <div 
      ref={mainRef} 
      className="bg-[#022C22] w-full overflow-x-hidden relative text-[#F4F4F2] [&::selection]:bg-[#10B981] [&::selection]:text-white"
    >

      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[150vw] h-auto opacity-5 z-0 pointer-events-none flex items-center justify-center text-[#10B981]">
        <TenantFirstAidLogo />
      </div>
      
      <div className="fixed left-0 top-0 w-[12px] h-screen bg-[#064E3B] z-[1] opacity-80 border-r border-[#E6D5B8] pointer-events-none max-[950px]:hidden"></div>
      <div className="fixed right-0 top-0 w-[12px] h-screen bg-[#064E3B] z-[1] opacity-80 border-l border-[#E6D5B8] pointer-events-none max-[950px]:hidden"></div>
      
      <section className="min-h-[56vh] flex items-center justify-center py-10 px-5 relative z-[2]">
        <div className="p-[14px] backdrop-blur-[16px] w-[425px] shadow-[0_8px_32px_rgba(0,0,0,0.2)] rounded-[24px]">
          <div className="flex items-center justify-center gap-[7.5px] flex-wrap">
            <div className="w-[90px] h-[90px] flex items-center"><BeaverIcon /></div>
            <h1 className="text-[32px] max-[950px]:text-[2.5rem] m-0 font-black text-[#F4F4F2] drop-shadow-none">Tenant First Aid</h1>
          </div>
          <p className="mt-[25px] text-[#F4F4F2] text-[16px] leading-[1.8] font-medium"></p>
        </div>
      </section>

      <div className="w-full bg-[#E6D5B8]/10 backdrop-blur-[16px] relative z-[2] py-16 border-y border-[#E6D5B8]/20">
          <div className="text-white flex justify-center gap-[60px] max-w-[1200px] mx-auto max-[950px]:flex-col">
              <div className="flex-1 text-center">
                <div className="cursor-pointer mt-[20px] text-[#10B981] font-semibold">
                  <a href="/chat" className="no-underline"><h4 className="text-[32px] text-[#F4F4F2] border-b-[2px] border-[#10B981] pb-[15px] font-bold">Chat with Brainy<span className="pl-[10px]">→</span></h4></a>
                </div>
              </div>
              <div className="flex-1 text-center">
                <div className="cursor-pointer mt-[20px] text-[#10B981] font-semibold">
                  <a href="/letter" className="no-underline"><h4 className="text-[32px] text-[#F4F4F2] border-b-[2px] border-[#10B981] pb-[15px] font-bold">Draft a letter<span className="pl-[10px]">→</span></h4></a>
                </div>
              </div>
          </div>
      </div>

      <section className="max-w-[1200px] my-[80px] mx-auto px-5 relative z-[2]">
        <div className="flex gap-[100px] items-start max-[950px]:flex-col-reverse max-[950px]:gap-[80px]">
            
            <div className="flex-1">
                <h3 className="text-[32px] mb-[40px] text-[#F4F4F2] font-extrabold">How to use Brainy</h3>
                <div className="flex flex-col">
                  {roadmapItems.map((item, i) => (
                    <div 
                      key={item.id}
                      className={clsx("flex gap-[30px]")}
                    >
                      <div className={clsx("flex flex-col items-center w-[30px]")}>
                        <div 
                          className={clsx(
                            "w-[20px] h-[20px] rounded-full border-2 z-[2]",
                            "bg-[#10B981] border-[#064E3B]"
                          )}
                        ></div>
                        
                        {i === 0 && (
                          <div className={clsx("w-[2px] flex-1 bg-white/20")}></div>
                        )}
                      </div>

                      <div className={clsx("flex-1 pb-[40px]")}>

                        <h4 
                          className={clsx(
                            "text-[1.6rem] my-2",
                            "text-[#F4F4F2]"
                          )}
                        >
                          {item.title}
                        </h4>
                        
                        <p 
                          className={clsx(
                            "leading-[1.6] opacity-90",
                            "text-[#F4F4F2]"
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
          <div className="flex-[1.5] relative max-[950px]:pr-0 max-[950px]:mt-[60px] max-[950px]:w-[100vw] max-[950px]:-ml-[20px]">
              <div className="w-full relative overflow-visible">
                
                <div className="relative w-full overflow-visible h-auto">
                  <div className="w-full h-auto invisible pt-[25px] pb-[15px] px-[15px] block border border-transparent">
                    <img src={letterImages[0].src} alt="" aria-hidden="true" className="w-full h-auto block" />
                  </div>

                  {letterImages.map((img, id) => (
                    <div 
                      key={id}
                      className="absolute top-[10px] left-0 w-full h-auto transition-all duration-[1270ms] ease-[cubic-bezier(0.34,1.56,0.64,1)] cursor-pointer shadow-[0_25px_50px_rgba(0,0,0,0.4)] border border-[#E6D5B8]/30 bg-[#E6D5B8]/70 backdrop-blur-[12px] p-[15px] rounded-[16px] box-border" 
                      style={getCardStyle(id)} 
                      onClick={handleNextLetter}
                    >
                      <img src={img.src} alt="Letter" className="w-full h-auto block" />
                    </div>
                  ))}
                </div>
                
                <div 
                  onClick={handleNextLetter} 
                  className="absolute right-0 top-1/2 -translate-y-1/2 bg-[#E6D5B8] border-2 border-[#022C22] rounded-full w-[64px] h-[64px] flex items-center justify-center cursor-pointer transition-all duration-500 ease-in-out z-30 shadow-[0_8px_20px_rgba(0,0,0,0.5)] max-[950px]:right-[20px] hover:-translate-y-1/2 hover:scale-[1.15] hover:!bg-[#10B981] hover:!text-[#022C22] hover:!border-[#10B981]"
                >
                  <ChevronRight color="#022C22" />
                </div>
              </div>

              <p className="text-center text-[#10B981] mt-[36px] text-[1rem] italic font-bold w-full block">
                Example outputs generated by Brainy
              </p>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="max-w-[1200px] my-[80px] mx-auto px-5 relative z-[2]">
        <div className="w-full">
          <h2 className="text-center mb-[20px] text-[#F4F4F2] text-[36px] font-extrabold">Why ask Brainy?</h2>
          <p className="text-center mt-[10px] mb-[50px] text-[1.4rem] text-[#34D399] font-semibold">
            Brainy uses a <span className="text-[#E6D5B8] font-bold underline decoration-[#10B981]">Retrieval-Augmented Generation</span> approach to look up information from curated legal sources
          </p>
          <div className="flex gap-[40px] mt-[50px] max-[950px]:flex-col">
                <div className="flex-1 bg-[#E6D5B8]/10 backdrop-blur-[16px] p-8 border border-[#E6D5B8]/20 rounded-[24px] shadow-[0_10px_25px_rgba(0,0,0,0.2)]">
                  <h4 className="text-[1.3rem] font-bold mb-4 flex items-center gap-4 text-[#F4F4F2]"><AirVentIcon size={24} color="#10B981" /> Retrieve</h4>
                  <p className="text-[1rem] text-[#F4F4F2] leading-[1.6]">Brainy retrieves the most relevant information about Oregon housing law, including</p>
                  <ul className="list-disc pl-4">
                    {Object.entries(REFERENCED_LAW_LIST).map(([key, reference]) => (
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
                    ))}
                  </ul>
                </div>
                <div className="flex-1 bg-[#E6D5B8]/10 backdrop-blur-[16px] p-8 border border-[#E6D5B8]/20 rounded-[24px] shadow-[0_10px_25px_rgba(0,0,0,0.2)]">
                  <h4 className="text-[1.3rem] font-bold mb-4 flex items-center gap-4 text-[#F4F4F2]"><ChartIcon size={24} color="#10B981" /> Augment</h4>
                  <p className="text-[1rem] text-[#F4F4F2] leading-[1.6]">Brainy combines what it finds with the questions the user asks.</p>
                </div>
                <div className="flex-1 bg-[#E6D5B8]/10 backdrop-blur-[16px] p-8 border border-[#E6D5B8]/20 rounded-[24px] shadow-[0_10px_25px_rgba(0,0,0,0.2)]">
                  <h4 className="text-[1.3rem] font-bold mb-4 flex items-center gap-4 text-[#F4F4F2]"><ActivityIcon size={24} color="#10B981" /> Generate</h4>
                  <p className="text-[1rem] text-[#F4F4F2] leading-[1.6]">Brainy writes a clear, concise answer.</p>
                </div>
          </div>
        </div>
      </section>

      <section id="compare" className="max-w-[1100px] my-[80px] mx-auto px-5 relative z-[2] max-[550px]:px-0">
        <h2 className="text-center px-[10vw] mb-[20px] text-[#F4F4F2] text-[36px] font-extrabold">Which approach is right for you?</h2>
        <div className="bg-[#E6D5B8]/10 backdrop-blur-[16px] border border-[#E6D5B8]/20 p-12 shadow-[0_15px_40px_rgba(0,0,0,0.2)] rounded-[24px] overflow-hidden max-[950px]:overflow-x-auto max-[950px]:p-6 max-[950px]:pl-0">
          <div className="grid grid-cols-4 gap-[1px] bg-[#E6D5B8]/10 max-[950px]:min-w-[700px] [&>div:nth-child(4n+1)]:max-[950px]:sticky [&>div:nth-child(4n+1)]:max-[950px]:left-0 [&>div:nth-child(4n+1)]:max-[950px]:z-10 [&>div:nth-child(4n+1)]:max-[950px]:border-r [&>div:nth-child(4n+1)]:max-[950px]:border-[#E6D5B8]/20 [&>div:nth-child(4n+1)]:max-[950px]:bg-[#0E362D] [&>div:nth-child(1)]:max-[950px]:!bg-[#064E3B]">
            <div className="p-5 font-bold bg-[#064E3B]/80 text-[#F4F4F2] text-center"></div>
            <div className="p-5 font-bold bg-[#064E3B]/80 text-[#F4F4F2] text-center">Tenant First Aid</div>
            <div className="p-5 font-bold bg-[#064E3B]/80 text-[#F4F4F2] text-center">Traditional Legal Aid</div>
            <div className="p-5 font-bold bg-[#064E3B]/80 text-[#F4F4F2] text-center">ChatGPT</div>
            
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium">Always available</div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center font-bold flex items-center justify-center"><CheckCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><XCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><CheckCircle /></div>

            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium">Always free</div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#42FFBC] text-center font-bold flex items-center justify-center"><CheckCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><XCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><XCircle /></div>
            
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium">No eligibility requirements</div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center font-bold flex items-center justify-center"><CheckCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><XCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><CheckCircle /></div>

            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium">Provides legal advice</div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center font-bold flex items-center justify-center"><XCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><CheckCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><XCircle /></div>

            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium">Only references relevant laws</div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center font-bold flex items-center justify-center"><CheckCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><CheckCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><XCircle /></div>
            
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium">Direct advocacy with court/landlords</div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center font-bold flex items-center justify-center"><XCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><CheckCircle /></div>
            <div className="p-5 bg-[#E6D5B8]/5 text-[#F4F4F2] text-center flex items-center justify-center font-medium"><XCircle /></div>
          </div>
        </div>
      </section>

      <section className="max-w-[1200px] my-[80px] mx-auto px-5 relative z-[2] text-center mb-[80px]">
        <div>
          <a href="/privacy-policy" className="text-[#10B981] text-[1.2rem] underline cursor-pointer font-bold">
            Privacy Policy
          </a>
          <p className="mt-[15px] text-[#F4F4F2] opacity-80 text-[1rem]">
            We don't store any of the information you input either in the session or on any servers
          </p>
        </div>
      </section>

      <section className="max-w-[1200px] my-[80px] mx-auto px-5 relative z-[2] text-center mb-[80px]">
        <div>
          <a href="/disclaimer" className="text-[#10B981] text-[1.2rem] underline cursor-pointer font-bold">
            Disclaimer
          </a>
          <p className="text-[#F4F4F2] opacity-80 text-[1rem] max-w-[800px] mx-auto leading-[1.6]">
            The information provided by this chatbot is general information only and does not constitute legal advice. While Tenant First Aid strives to keep the content accurate and up to date, completeness and accuracy is not guaranteed. If you have a specific legal issue or question, consider contacting a qualified attorney or a local legal aid clinic for personalized assistance. For questions related to Tenant First Aid, contact <a href="mailto:michael@qiu-qiulaw.com" className="text-[#10B981]">michael@qiu-qiulaw.com</a>.
          </p>
        </div>
      </section>

      <section className="max-w-[1200px] my-[80px] mx-auto px-5 relative z-[2]">
        <div className="p-16 bg-[#E6D5B8]/10 backdrop-blur-[16px] border border-[#E6D5B8]/20 text-center rounded-[24px] shadow-[0_15px_40px_rgba(0,0,0,0.2)]">
          <h2 className="text-[36px] font-extrabold text-[#F4F4F2] mb-[20px]">Who We Are</h2>
          <p className="text-[1.3rem] leading-[1.9] text-[#F4F4F2] font-normal">
            <strong>Tenant First Aid</strong> is a volunteer-built program by <a href="https://www.codepdx.org/" className="text-[#10B981]">Code PDX</a> and <a href="mailto:michael@qiu-qiulaw.com" className="text-[#10B981]">Qiu Qiu Law</a>. 
          </p>
        </div>
      </section>

      <section className="h-[16vh] flex items-center justify-center relative overflow-hidden">
        <div className="text-center z-[3]">
          <h1 className="text-[clamp(2.6rem,10vw,2.6rem)] font-black text-[#F4F4F2]">Get in touch</h1>
        </div>
      </section>

      <HPFeedbackForm nameValue="" subjectValue="" feedbackValue="" />
    </div>
    </>
  );
};

export default HomePage;