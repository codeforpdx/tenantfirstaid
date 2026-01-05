import MessageWindow from "./pages/Chat/components/MessageWindow";
import useMessages from "./hooks/useMessages";
import { useLetterContent } from "./hooks/useLetterContent";
import ChatDisclaimer from "./pages/Chat/components/ChatDisclaimer";
import MessageContainer from "./shared/components/MessageContainer";
import BeaverIcon from "./shared/components/BeaverIcon";
import TenantFirstAidLogo from "./shared/components/TenantFirstAidLogo";

export default function Chat() {
  const { addMessage, messages, setMessages } = useMessages();
  const isOngoing = messages.length > 0;
  const { letterContent } = useLetterContent(messages);
  let city = 'Portland';
  let locationString = 'Oregon';

  return (
    <div className="flex pt-16 h-screen items-center justify-center">
            <div className="flex px-4 gap-4 items-center">
              <div 
            style={{position: 'absolute', top: '10%', left: "42vw", flexDirection: 'column', alignItems: 'center', minHeight: '230px', justifyContent: 'center'}}>
                <BeaverIcon />
              </div>
              {/* <div className="w-full">
                <p className="text-center text-[#888]">
                  {city === "other"
                    ? "Unfortunately, we can only answer questions related to tenant rights in Oregon at this time."
                    : `Welcome to Tenant First Aid! ${locationString ? `I can help answer your questions about tenant rights in ${locationString}.` : "Start by filling the form below."}`}
                </p>
              </div> */}
            <div className="flex-l justify-between mw8 center white pa4"
                  style={{background: 'green', marginBottom: '5%', width: '100vw', borderRadius: '8px', display: "flex", justifyContent: "space-between", minHeight: "150px", alignItems: "center", paddingLeft: "200px", paddingRight: "200px"}}>
                        <div className="w-50-l bt bw2 b--blue pt4 mr5-l mb5">
                          <h4 className="f3 f2-ns fw9 lh-title mt0 mb4"
                          style={{fontSize: "32px", color: "white", borderBottom: "2px solid white"}}>
                            Free advice!
                          </h4>
                          <div
                            className="f4 f3-ns fw7 link light-blue hover-white"
                            onClick={() => window.scrollTo(0, 0)}
                            style={{fontSize: "16px", color: "white"}}
                          >
                            Chat with tenant rights bot.
                            <span
                              className="fas fa-arrow-right f5 lh-solid pt1 pl2"
                              aria-hidden="true"
                            ></span>
                          </div>
                        </div>
            
                        <div className="w-50-l bt bw2 b--blue pt4 ml5-l mb5">
                          <h4 className="f3 f2-ns fw9 lh-title mt0 mb4"
                          style={{fontSize: "32px", color: "white", borderBottom: "2px solid white"}}>
                            Draft a letter to your landlord.
                          </h4>
            
                          <div
                            className="f4 f3-ns fw7 link light-blue hover-white"
                            onClick={() => window.scrollTo(0, 0)}
                            style={{fontSize: "16px", color: "white"}}
                          >
                            Get started
                            <span
                              className="fas fa-arrow-right f5 lh-solid pt1 pl2"
                              aria-hidden="true"
                            ></span>
                          </div>
                        </div>
                      </div>
                    </div>

      {/* <div className="flex-1 h-full sm:h-auto items-center transition-all duration-300">
        <MessageContainer isOngoing={isOngoing} letterContent={letterContent}>
          <div
            className={`flex flex-col ${letterContent === "" ? "flex-1" : "flex-1/3"}`}
          >
            <MessageWindow
              messages={messages}
              addMessage={addMessage}
              setMessages={setMessages}
              isOngoing={isOngoing}
            />
          </div>
        </MessageContainer>
        <ChatDisclaimer isOngoing={isOngoing} />
      </div> */}
    </div>
  );
}
