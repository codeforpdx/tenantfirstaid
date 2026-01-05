import React, { useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import { Mail, MessageSquare, ArrowRight, ShieldCheck, Scale, MapPin, AlertCircle } from 'lucide-react';
import BeaverIcon from './shared/components/BeaverIcon';

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const HP3 = () => {
  const containerRef = useRef(null);

  const steps = [
    { id: 1, title: "Chatbot for Rights", desc: "Free answers to your tenant rights questions.", icon: <MessageSquare /> },
    { id: 2, title: "Powered by Gemini", desc: "Uses advanced AI for guidance, not legal advice.", icon: <Scale /> },
    { id: 3, title: "Oregon Specific", desc: "Tailored specifically to Oregon local laws.", icon: <MapPin /> },
    { id: 4, title: "Safe & Private", desc: "Your data is never stored on our servers.", icon: <AlertCircle /> },
  ];

  useGSAP(() => {
    const sections = gsap.utils.toArray('.reveal-section');
    sections.forEach((section) => {
      gsap.fromTo(section, 
        { opacity: 0, y: 30 },
        { 
          opacity: 1, 
          y: 0, 
          duration: 0.8, 
          ease: "power2.out",
          scrollTrigger: {
            trigger: section,
            start: "top 85%",
            toggleActions: "play none none reverse"
          }
        }
      );
    });

    gsap.to(".floating-beaver", {
       y: -15,
       repeat: -1,
       yoyo: true,
       duration: 2,
       ease: "sine.inOut"
    });
  }, { scope: containerRef });

  return (
    <div ref={containerRef} className="bg-[#022c22] text-white font-sans selection:bg-green-200">
      
      {/* 1. HERO SECTION - TEXT BELOW BEAVER */}
      <header className="min-h-[60vh] flex flex-col items-center justify-center relative px-4 text-center">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#10b98110_0%,_transparent_75%)] opacity-50" />
        
        <div className="flex flex-col items-center gap-6 z-10">
          <div className="floating-beaver">
            <BeaverIcon size={120} />
          </div>

          <div className="max-w-2xl">
            <p className="text-xl md:text-2xl font-medium leading-relaxed opacity-90">
              Tenant First Aid is a chatbot that can provide you with information about housing law in Oregon and help you write letters to your landlord. You can use this free tool to help yourself, or help others.
            </p>
          </div>
        </div>
      </header>

      {/* 2. CTA SECTION */}
      <div className="user-cta-block relative z-20">
        <div className="flex flex-col md:flex-row justify-between items-center bg-green-700 w-full min-h-[200px] py-12 px-6 md:px-48 rounded-lg shadow-2xl">
          <div className="w-full md:w-5/12 border-b-2 md:border-b-0 md:border-l-2 border-white/30 p-4 mb-8 md:mb-0">
            <h4 className="text-3xl font-black mb-4">Get Answers</h4>
            <div className="flex items-center gap-2 cursor-pointer hover:translate-x-2 transition-transform" onClick={() => window.scrollTo(0, 0)}>
              <span className="text-lg font-bold">Start Chatting</span>
              <ArrowRight size={20} />
            </div>
          </div>
          
          <div className="w-full md:w-5/12 border-b-2 md:border-b-0 md:border-l-2 border-white/30 p-4">
            <h4 className="text-3xl font-black mb-4">Write a Letter</h4>
            <div className="flex items-center gap-2 cursor-pointer hover:translate-x-2 transition-transform" onClick={() => window.scrollTo(0, 0)}>
              <span className="text-lg font-bold">Get Started</span>
              <ArrowRight size={20} />
            </div>
          </div>
        </div>
      </div>

      {/* 3. THE PROCESS - VERTICAL ALIGNMENT */}
      <section className="py-32 px-6 max-w-4xl mx-auto">
        <div className="reveal-section text-center mb-20">
          <h2 className="text-4xl md:text-5xl font-black mb-4 tracking-tighter text-white uppercase">The Process</h2>
          <div className="w-20 h-1.5 bg-green-500 mx-auto rounded-full" />
        </div>

        {/* Vertical Stack */}
        <div className="flex flex-col gap-10">
          {steps.map((step, i) => (
            <div 
              key={i} 
              className="reveal-section flex flex-col md:flex-row items-center gap-8 bg-emerald-900/20 border border-white/5 p-10 rounded-[40px] hover:border-green-500/40 transition-all group"
            >
              <div className="text-green-400 group-hover:scale-110 transition-transform duration-300 flex-shrink-0">
                {React.cloneElement(step.icon, { size: 48 })}
              </div>
              
              <div className="text-center md:text-left">
                <span className="text-xs font-bold text-green-500 tracking-widest uppercase">Step 0{step.id}</span>
                <h3 className="text-2xl font-bold mt-2 mb-3 leading-tight">{step.title}</h3>
                <p className="text-emerald-100/70 leading-relaxed text-lg">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. NARRATIVE SECTIONS */}
      <section className="py-24 bg-emerald-950/20">
        <div className="max-w-6xl mx-auto px-6 space-y-40">
          <div className="reveal-section flex flex-col md:flex-row items-center gap-12 md:gap-24">
            <div className="flex-1">
              <h2 className="text-5xl font-black leading-tight mb-8 tracking-tighter">Built for <span className="text-green-400">Oregon</span> Tenants.</h2>
              <p className="text-lg text-emerald-100/70 leading-relaxed mb-8">
                Navigating local housing statutes doesn't have to be a solo mission. Our platform combines conversational AI with specific local legislative knowledge.
              </p>
              <button className="flex items-center gap-2 font-bold text-green-400 hover:text-green-300 transition-colors group">
                Explore Oregon Statutes <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
            <div className="flex-1 w-full bg-emerald-900/30 rounded-[48px] border border-white/5 p-12 flex flex-col items-center justify-center text-center">
               <MapPin size={80} className="text-green-500/20 mb-4" />
               <p className="text-green-500/40 font-bold uppercase tracking-widest text-xs">Verified Region: OR</p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. FOOTER / FINAL CTA */}
      <section className="py-32 flex flex-col items-center justify-center text-center px-4">
        <h1 className="text-6xl md:text-8xl font-black text-white hover:text-green-400 transition-colors duration-500 leading-none mb-16 tracking-tighter uppercase"
            style={{ fontSize: '42px' }}>
          Write us  an <span className="text-green-400">Email</span>
        </h1>
        <div className="flex flex-col sm:flex-row gap-6">
          <button className="px-12 py-5 rounded-full bg-green-500 text-green-950 font-black text-xl hover:bg-white transition-all shadow-xl shadow-green-500/20">
            Launch Chatbot
          </button>
          <button className="px-12 py-5 rounded-full border border-white/20 text-white font-bold text-xl hover:bg-white/5 transition-all">
            Contact Support
          </button>
        </div>
        <footer className="mt-32 text-emerald-100/20 text-xs uppercase tracking-[0.2em] font-medium">
          © 2026 Tenant First Aid • Dedicated to Oregon Tenants
        </footer>
      </section>
    </div>
  );
};

export default HP3;