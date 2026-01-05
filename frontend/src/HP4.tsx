import React from 'react';
import { MessageSquare, PenTool, ShieldCheck, Database, Zap, AirVent, FileText, ChartNoAxesColumn, AlignEndHorizontal, Activity } from 'lucide-react';
import BeaverIcon from './shared/components/BeaverIcon';
import TFALAbbreviated from './shared/components/TFALAbbreviated';
import exampleLetter from '../public/example-lettter.png'

const HP4 = () => {
  return (
    <div className="min-h-screen bg-white text-slate-800 font-sans">
      {/* Hero Section */}
      <header className="bg-gradient-to-br from-blue-50 to-indigo-50 py-16 md:py-24 text-center"
      style={{paddingTop: "175px"}}>
        <div className="">
          <h1 className="text-4xl md:text-6xl font-extrabold text-slate-900 mb-8 tracking-tight flex flex-col items-center gap-4">
            <BeaverIcon />
          </h1>
          <p className="text-xl md:text-2xl text-slate-600 mb-10 leading-relaxed max-w-4xl mx-auto">
            Tenant First Aid is a chatbot that can provide you with information about housing law in Oregon and help you write letters to your landlord. You can use this free tool to help yourself, or help others
          </p>
          
          {/* Action Bar: Buttons with sharp corners (removed rounded-xl) */}
          <div className="flex flex-col md:flex-row justify-center gap-4"
          style={{width: "100vw", display: "flex", height: "200px", alignItems: "center", justifyContent: "space-around", background: "rgb(31,88,79)"}}>
            <button className="flex items-center justify-center gap-2 bg-transparent border-b-2 border-white text-white px-8 py-4 font-bold hover:bg-white/10 transition transform hover:-translate-y-1">
              <MessageSquare size={20} /> Get answers
            </button>
            <button className="flex items-center justify-center gap-2 bg-transparent border-b-2 border-white text-white px-8 py-4 font-bold hover:bg-white/10 transition transform hover:-translate-y-1">
              <PenTool size={20} /> Write a letter
            </button>
          </div>
        </div>
      </header>

      {/* About Section - Vertically Stacked Text */}
      <section id="about" className="py-24 px-6 max-w-7xl mx-auto overflow-hidden">
        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-16">
          Tenant First Aid – it’s all in the name
        </h2>

        <div className="flex flex-col md:flex-row items-center gap-16 md:gap-12">
          {/* Left Column: Vertical Stack */}
          <div className="flex flex-col gap-8 md:w-1/2">
            <div className="w-full text-lg text-slate-600 leading-relaxed">
              <p className="p-2">
                Tenant First Aid includes a chatbot (“Fredrick de Loueur”) designed to help Oregon tenants understand their rights if they're facing eviction or having other issues with their landlords. Chatbot only handles housing-related questions, so if the user’s issue is about something else (like family law or criminal charges), we won’t be able to help.
              </p>
            </div>
            <div className="w-full">
              <div 
                className="p-8 rounded-3xl text-lg text-slate-600 leading-relaxed bg-slate-100"
                style={{
                  background: 'linear-gradient(to right, rgb(44, 104, 54) 0%, rgb(241, 245, 249) 2%, rgb(241, 245, 249) 101%)'
                }}
              >
                Tenant First Aid is meant to provide clear and immediate guidance - like legal "first aid". If your situation is urgent or serious, we recommend consulting with an attorney that specializes in Oregon housing law. In particular, Tenant First Aid is not your attorney, and is not an attorney at all. But as a first step, it can provide relevant legal information and assist with writing legally required correspondences with your landlord.
              </div>
            </div>
          </div>
          <div className="md:w-1/2 flex justify-center items-center py-20">
            <div className="transform scale-[4.8] transition-transform duration-500">
              <TFALAbbreviated />
            </div>
          </div>
        </div>
      </section>

      {/* How it Works / RAG Section - Vertically Stacked with Image Column */}
      <section id="how-it-works" className="py-24 bg-slate-900 text-white px-6">
        <div className="max-w-7xl mx-auto">
          <p className="text-xl text-slate-300 mb-12 max-w-3xl">
            Tenant First Aid is powered by AI. But unlike using other off-the-shelf AI chatbots (like ChatGPT, Gemini, Grok, etc.), Tenant First Aid uses a <span className="text-blue-400 font-mono">RAG approach</span> to look up information from trusted legal sources (like Oregon housing laws and tenant guides).
          </p>
          
          <div className="flex flex-col md:flex-row gap-12 items-start">
            {/* Left Column: Vertically stacked technical steps */}
            <div className="md:w-1/2 flex flex-col gap-6">
              <h3 className="text-blue-400 font-bold uppercase tracking-widest mb-2 text-sm">Here’s how it works:</h3>
              
              <div className="bg-slate-800 p-8 rounded-2xl border border-slate-700">
                <h4 className="text-xl font-bold mb-3 flex items-center gap-3">
                  <AirVent size={24} className="text-blue-400" /> Retrieve
                </h4>
                <p className="text-slate-400">Chatbot searches legal knowledge base for the most relevant information about Oregon housing law.</p>
              </div>

              <div className="bg-slate-800 p-8 rounded-2xl border border-slate-700">
                <h4 className="text-xl font-bold mb-3 flex items-center gap-3">
                  <ChartNoAxesColumn size={24} className="text-blue-400" /> Augment
                </h4>
                <p className="text-slate-400">Chatbot combines what it finds with the question the user asks.</p>
              </div>

              <div className="bg-slate-800 p-8 rounded-2xl border border-slate-700">
                <h4 className="text-xl font-bold mb-3 flex items-center gap-3">
                  <Activity size={24} className="text-blue-400" /> Generate
                </h4>
                <p className="text-slate-400">Chatbot writes a clear, concise answer.</p>
              </div>
            </div>

            {/* Right Column: Letter Image Snapshot Area */}
            <div className="md:w-1/2 w-full mt-12 md:mt-0">
              <div className="sticky top-32">
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-6 shadow-2xl overflow-hidden">
                    <img src={exampleLetter} alt="Letter Snapshot" className="w-full h-auto rounded shadow-sm" />
                </div>
                <p className="text-center text-slate-500 mt-6 text-sm italic">Example of a letter generated by the process</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Privacy Section */}
      <section id="privacy" className="py-24 px-6">
        <div className="max-w-3xl mx-auto bg-red-50 p-10 rounded-3xl border border-red-100 text-center">
          <h2 className="text-3xl font-bold text-slate-900 mb-6">Privacy</h2>
          <p className="text-lg text-slate-700 mb-0 leading-relaxed">
            Tenant First Aid does not save your answers after you leave this website. There is no way for us to retrieve previous sessions. Consider saving your work in a separate document before leaving the Chat sessions.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-100 py-16 px-6">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-end items-center gap-8">
          <button className="bg-slate-900 text-white px-8 py-4 rounded-xl font-bold hover:bg-slate-800 transition">
            Partner with us
          </button>
        </div>
      </footer>
    </div>
  );
};

export default HP4;