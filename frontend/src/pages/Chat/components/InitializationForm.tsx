import { IMessage } from "../../../hooks/useMessages";
import BeaverIcon from "../../../shared/components/BeaverIcon";
import { useEffect, useState } from "react";
import { buildChatUserMessage } from "../utils/formHelper";
import { streamText } from "../utils/streamHelper";
import SelectField from "./SelectField";
import { Link } from "react-router-dom";
import useHousingContext from "../../../hooks/useHousingContext";
import {
  ALL_TOPIC_OPTIONS,
  CITY_SELECT_OPTIONS,
  HOUSING_OPTIONS,
  LETTERABLE_TOPIC_OPTIONS,
  NONLETTERABLE_TOPIC_OPTIONS,
} from "../../../shared/constants/constants";
import { scrollToTop } from "../../../shared/utils/scrolling";
import AutoExpandText from "./AutoExpandText";

const NONLETTERABLE_TOPICS = Object.keys(NONLETTERABLE_TOPIC_OPTIONS);

interface Props {
  addMessage: (args: {
    city: string | null;
    state: string;
  }) => Promise<ReadableStreamDefaultReader<Uint8Array> | undefined>;
  setMessages: React.Dispatch<React.SetStateAction<IMessage[]>>;
}

export default function InitializationForm({ addMessage, setMessages }: Props) {
  const {
    housingLocation,
    city,
    housingType,
    tenantTopic,
    issueDescription,
    handleHousingLocation,
    handleCityChange,
    handleHousingChange,
    handleTenantTopic,
    handleIssueDescription,
    handleFormReset,
  } = useHousingContext();
  const [initialUserMessage, setInitialUserMessage] = useState("");
  const locationString = city
    ? city.charAt(0).toUpperCase() + city.slice(1)
    : null;

  const handleLocationChange = (key: string | null) => {
    handleCityChange(key);
    handleHousingLocation({
      city:
        CITY_SELECT_OPTIONS[key as keyof typeof CITY_SELECT_OPTIONS]?.city ||
        null,
      state:
        CITY_SELECT_OPTIONS[key as keyof typeof CITY_SELECT_OPTIONS]?.state ||
        null,
    });
  };

  const handleInitialInput = async () => {
    // Initial user message
    const userMessageId = Date.now().toString();
    setMessages((prev) => [
      ...prev,
      { role: "user", content: initialUserMessage, messageId: userMessageId },
    ]);

    await streamText({
      addMessage,
      setMessages,
      housingLocation,
    });
  };

  useEffect(() => {
    const { userMessage: initialUserMessage } = buildChatUserMessage(
      housingLocation,
      housingType,
      tenantTopic,
      issueDescription,
    );
    setInitialUserMessage(initialUserMessage);
  }, [housingLocation, issueDescription, housingType, tenantTopic]);

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        handleInitialInput();
      }}
    >
      <div className="flex px-4 gap-4 items-center justify-center">
        <div>
          <BeaverIcon />
        </div>
        <div className="">
          <p className="text-xl sm:text-2xl text-center">
            Welcome to Tenant First Aid!
          </p>
        </div>
      </div>
      <div>
        <div className="border rounded-lg px-4 py-3">
          <p>Things to keep in mind!</p>
          <ul className="list-disc pl-4">
            <li>Tenants have rights under state and local law.</li>
            <li>
              The type of housing you live in may determine what legal
              protections apply to you.
            </li>
            <li>
              In most cases, landlords must go through a specific legal process
              in order to get you to move out (eviction).
            </li>
          </ul>
        </div>
        <p className="pt-2 px-4">
          I'm an interactive AI. We can start by filling the form below.
          Depending on the topic, I could help generate a letter to address your
          housing situation or answer your questions.
        </p>
      </div>
      <div>
        <SelectField
          name="city"
          value={city || ""}
          description="Select your location"
          handleFunction={handleLocationChange}
        >
          {Object.entries(CITY_SELECT_OPTIONS).map(([key, option]) => (
            <option key={key} value={key}>
              {option.label}
            </option>
          ))}
        </SelectField>
        <AutoExpandText isExpanded={Boolean(city)}>
          {city === "other"
            ? "Unfortunately, we can only answer questions related to tenant rights in Oregon at this time."
            : `${locationString ? `I can help answer your questions about tenant rights in ${locationString}.` : ""}`}
        </AutoExpandText>
      </div>
      <SelectField
        name="housing type"
        value={housingType || ""}
        description="Select your housing type"
        handleFunction={handleHousingChange}
      >
        {HOUSING_OPTIONS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </SelectField>
      <div>
        <SelectField
          name="tenant topic"
          value={tenantTopic || ""}
          description="Select your topic"
          handleFunction={handleTenantTopic}
        >
          <optgroup label="--Letterable--">
            {Object.entries(LETTERABLE_TOPIC_OPTIONS).map(([key, option]) => (
              <option key={key} value={key}>
                {option.label}
              </option>
            ))}
          </optgroup>
          <optgroup label="--Non-Letterable--">
            {Object.entries(NONLETTERABLE_TOPIC_OPTIONS).map(
              ([key, option]) => (
                <option key={key} value={key}>
                  {option.label}
                </option>
              ),
            )}
          </optgroup>
        </SelectField>
        <AutoExpandText isExpanded={Boolean(tenantTopic)}>
          <div className="px-4">
            Here are some examples of questions I can help with:
            <ul className="list-disc pl-4">
              {ALL_TOPIC_OPTIONS[
                tenantTopic as keyof typeof ALL_TOPIC_OPTIONS
              ]?.example.map((question, index) => (
                <li key={`${tenantTopic}-${index}`}>
                  {question.split(/(_)/).map((part, i) => {
                    if (!part.startsWith("_")) return part;
                    return (
                      <span key={i} className="inline-block w-[3ch] border-b" />
                    );
                  })}
                </li>
              ))}
            </ul>
          </div>
        </AutoExpandText>
      </div>
      <div>
        <textarea
          className="h-25 md:h-20 w-full"
          placeholder="Briefly describe your specific housing situation or question about housing."
          onChange={handleIssueDescription}
        />
      </div>

      <div className="flex justify-center gap-4">
        <button
          className={`
            text-red-dark
            border border-red-medium hover:border-red-dark
            hover:bg-red-light
            ${city === "other" ? "opacity-50" : ""}`}
          type="reset"
          onClick={handleFormReset}
        >
          Reset
        </button>
        <button
          className={`
            text-green-dark
            border border-green-medium hover:border-green-dark
            hover:bg-green-light
            ${city === "other" ? "opacity-50" : ""}`}
          style={{
            cursor: city === "other" ? "not-allowed" : "pointer",
          }}
          type="submit"
          aria-label="enter chat"
          title="Enter Chat"
          disabled={city === "other"}
          onClick={() => scrollToTop()}
        >
          Start Chat
        </button>
        {housingLocation &&
          housingType &&
          tenantTopic &&
          !NONLETTERABLE_TOPICS.includes(tenantTopic) &&
          issueDescription && (
            <Link
              to="letter"
              className={`
                flex items-center
                py-1 px-4
                border rounded-md border-blue-medium hover:border-blue-dark
                font-semibold text-center text-blue-dark 
                hover:bg-blue-light no-underline
                ${city === "other" ? "opacity-50" : ""}`}
              style={{
                cursor: city === "other" ? "not-allowed" : "pointer",
              }}
              aria-disabled={city === "other"}
              aria-label="generate letter"
              title="Generate Letter"
              onClick={(e) => {
                if (NONLETTERABLE_TOPICS.includes(tenantTopic)) {
                  e.preventDefault();
                  e.stopPropagation();
                } else {
                  scrollToTop();
                }
              }}
            >
              Generate Letter
            </Link>
          )}
      </div>
    </form>
  );
}
