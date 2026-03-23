import { useState } from "react";
import letterImages from "./LetterImages";
import ChevronRight from "../../../shared/components/ChevronRight";

export default function LetterCarousel() {
  const [activeLetterIndex, setActiveLetterIndex] = useState(0);

  const handleNextLetter = () => {
    setActiveLetterIndex((prev) => (prev + 1) % letterImages.length);
  };
  const getCardStyle = (index: number) => {
    const position =
      (index - activeLetterIndex + letterImages.length) % letterImages.length;

    if (position === 0) {
      return {
        zIndex: 10,
        transform: "scale(1) translateX(0) translateY(0) rotate(0deg)",
        opacity: 1,
      };
    } else if (position === 1) {
      return {
        zIndex: 9,
        transform:
          "scale(0.98) translateX(-20px) translateY(-25px) rotate(-2deg)",
        opacity: 0.8,
      };
    } else {
      return {
        zIndex: 8,
        transform:
          "scale(0.96) translateX(-40px) translateY(-50px) rotate(-4deg)",
        opacity: 0.6,
      };
    }
  };
  return (
    <div className="w-full relative overflow-visible">
      <div className="relative w-full overflow-visible h-auto">
        <div className="w-full h-auto invisible pt-[25px] pb-[15px] px-[15px] block border border-transparent">
          <img
            src={letterImages[0].src}
            alt=""
            aria-hidden="true"
            className="w-full h-auto block"
          />
        </div>

        {letterImages.map((img, index: number) => (
          <div
            key={img.id}
            className="absolute top-2.5 left-0 w-full h-auto transition-all duration-[1270ms] ease-[cubic-bezier(0.34,1.56,0.64,1)] cursor-pointer shadow-[0_25px_50px_rgba(0,0,0,0.4)] border border-[#E6D5B8]/30 bg-[#E6D5B8]/70 backdrop-blur-md p-[15px] rounded-2xl box-border"
            style={getCardStyle(index)}
            onClick={handleNextLetter}
          >
            <img src={img.src} alt="Letter" className="w-full h-auto block" />
          </div>
        ))}
      </div>

      <div
        onClick={handleNextLetter}
        className="absolute right-0 top-1/2 -translate-y-1/2 bg-[#E6D5B8] border-2 border-emerald-950 rounded-full w-16 h-16 flex items-center justify-center cursor-pointer transition-all duration-500 ease-in-out z-30 shadow-[0_8px_20px_rgba(0,0,0,0.5)] max-[950px]:right-5 hover:-translate-y-1/2 hover:scale-[1.15] hover:!bg-emerald-500 hover:!text-emerald-950 hover:!border-emerald-500"
      >
        <ChevronRight color="#022C22" />
      </div>
    </div>
  );
}
