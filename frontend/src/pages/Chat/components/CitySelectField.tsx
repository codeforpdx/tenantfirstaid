import { useState } from "react";
import useMessages, { IMessage } from "../../../hooks/useMessages";

const CitySelectOptions = {
    "portland": {
        city: "portland",
        state: "or",
        label: "Portland"
    },
    "eugene": {
        city: "eugene",
        state: "or",
        label: "Eugene"
    },
    "oregon": {
        city: null,
        state: "or",
        label: "Other city in Oregon"
    },
    "other": {
        city: null,
        state: null,
        label: "City in another state"
    }
};

interface Props {
    setMessages: React.Dispatch<React.SetStateAction<IMessage[]>>;
}

export default function CitySelectField({ setMessages }: Props) {
    const [value, setCity] = useState<string | null>(null);
    const [invalidCity, setInvalidCity] = useState<boolean>(false);
    const { initSession } = useMessages();

    const handleCityChange = async (key: string | null) => {
        setCity(key);
        const city = CitySelectOptions[key as keyof typeof CitySelectOptions];
        if (city && city.state) {
            setInvalidCity(false);

            try {
                await initSession({ city: city.city, state: city.state });

                // Initial bot message that's not included in history
                const botMessageId = (Date.now() + 1).toString();
                setMessages((prev) => [
                    ...prev,
                    {
                        role: "assistant",
                        content: "Ask me anything about Oregon tenant rights and assistance.",
                        messageId: botMessageId,
                    },
                ]);
            } catch (error) {
                console.error("Error initializing session:", error);
                setInvalidCity(true);
            }
        } else {
            setInvalidCity(true);
        }
    };

    return (
        <div className="flex flex-col gap-2">
            <p className="text-center text-[#888] mb-10">
                {invalidCity ?
                    "Unfortunately we can only answer questions about tenant rights in Oregon right now." :
                    "Welcome to Tenant First Aid! I can answer your questions about tenant rights in Oregon. To get started, what city are you located in?"
                }
            </p>
            <select
                name="city"
                value={value || ""}
                onChange={e => handleCityChange(e.target.value)}
                className="p-3 border-1 border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
            >
                <option value="" disabled>
                    Select a city
                </option>
                {Object.entries(CitySelectOptions).map(([key, option]) => (
                    <option key={key} value={key}>
                        {option.label}
                    </option>
                ))}
            </select>
        </div>
    );
}