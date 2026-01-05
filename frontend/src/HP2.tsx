import React, { useState } from 'react';
import { Menu, X, ChevronDown, ChevronUp, Globe, ExternalLink, CheckCircle2 } from 'lucide-react';

const HP2 = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [activeFaq, setActiveFaq] = useState(null);

  const toggleFaq = (index) => {
    setActiveFaq(activeFaq === index ? null : index);
  };

  const navLinks = [
    { name: 'Home', href: '#' },
    { name: 'About Us', href: '#' },
    { name: 'FAQ', href: '#' },
  ];

  const faqs = [
    {
      question: "Why do I need a declaration?",
      answer: "When you file a petition with the court, you have the opportunity to attach a personal letter called a “declaration” explaining why you deserve a fresh start. The declaration letter is your opportunity to explain to a judge why you want your criminal record cleared or your charges reduced. A declaration can help your case by adding your personal reasons and motivation to your legal case."
    },
    {
      question: "Why does expungement or reclassification matter to me?",
      answer: "Expungement means that in most cases your past criminal record cannot be used against you when applying for a job, housing or student loans. Reclassification allows you to change past felony convictions to a misdemeanor, even if you have served a sentence and parole. Once the felony has been removed, you may be eligible for benefits not previously available to you."
    },
    {
      question: "Can law enforcement get a search warrant to access my data on this site?",
      answer: "No. Even if law enforcement were to search this site for your data, there would be no data to find. We do not store or save any of your data, ever. Once your data has left our site via download, it is your responsibility to keep your data secure."
    }
  ];

  return (
    <div className="min-h-screen bg-white font-sans text-gray-900 selection:bg-emerald-100">
      {/* --- NAVIGATION --- */}
      <nav className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-20 items-center">
            <div className="flex items-center">
              <div className="text-2xl font-bold text-emerald-800 flex items-center cursor-pointer">
                <span className="mr-2 text-3xl">📁</span> 
                <span className="tracking-tight">Expunge Assist</span>
              </div>
            </div>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center space-x-8">
              <div className="flex items-center space-x-4 mr-6 text-xs font-bold text-gray-500 uppercase tracking-widest">
                <button className="hover:text-emerald-700 transition-colors">ENG</button>
                <span className="text-gray-300">|</span>
                <button className="hover:text-emerald-700 transition-colors">ESP</button>
                <span className="text-gray-300">|</span>
                <button className="hover:text-emerald-700 transition-colors">KO</button>
              </div>
              {navLinks.map((link) => (
                <a key={link.name} href={link.href} className="text-gray-600 hover:text-emerald-700 font-semibold transition-colors">
                  {link.name}
                </a>
              ))}
              <button className="bg-emerald-700 text-white px-6 py-2.5 rounded-md font-bold hover:bg-emerald-800 transition-all shadow-md active:transform active:scale-95">
                START NOW
              </button>
            </div>

            {/* Mobile menu button */}
            <div className="md:hidden">
              <button onClick={() => setIsMenuOpen(!isMenuOpen)} className="text-gray-700 p-2">
                {isMenuOpen ? <X size={28} /> : <Menu size={28} />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Nav Menu */}
        {isMenuOpen && (
          <div className="md:hidden bg-white border-b px-4 pt-2 pb-8 space-y-4">
            {navLinks.map((link) => (
              <a key={link.name} href={link.href} className="block text-lg font-semibold text-gray-700 py-2 border-b border-gray-50">
                {link.name}
              </a>
            ))}
            <div className="flex space-x-6 py-2">
                <button className="text-sm font-bold text-emerald-800">ENGLISH</button>
                <button className="text-sm font-bold text-gray-500">ESPAÑOL</button>
                <button className="text-sm font-bold text-gray-500">한국어</button>
            </div>
            <button className="w-full bg-emerald-700 text-white py-4 rounded-md font-bold text-lg shadow-lg">
              START NOW
            </button>
          </div>
        )}
      </nav>

      {/* --- HERO SECTION --- */}
      <section className="py-16 md:py-28 bg-emerald-50/50">
        <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row items-center gap-12">
          <div className="md:w-3/5 text-center md:text-left">
            <h1 className="text-4xl md:text-6xl font-extrabold text-emerald-900 leading-[1.1] mb-8">
              A writing tool for people seeking expungement
            </h1>
            <p className="text-xl md:text-2xl text-gray-700 mb-10 leading-relaxed max-w-2xl">
              Expunge Assist helps you write a letter to a judge (a “declaration”). If you are applying to have your record expunged, a declaration can help.
            </p>
            <button className="bg-emerald-700 text-white px-12 py-5 rounded-md text-xl font-bold hover:bg-emerald-800 transition-all shadow-xl hover:shadow-emerald-200/50 active:transform active:scale-95">
              START NOW
            </button>
          </div>
          <div className="md:w-2/5 flex justify-center">
            <div className="w-full max-w-sm aspect-square bg-white rounded-2xl shadow-2xl border-8 border-white overflow-hidden flex items-center justify-center text-gray-400 italic bg-gradient-to-br from-emerald-100 to-green-50">
              <div className="text-center p-8">
                <div className="text-6xl mb-4">✍️</div>
                <p className="text-sm font-medium">Illustration: Writing your story</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* --- MISSION STATEMENT --- */}
      <section className="py-24">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-8 tracking-tight">What is Expunge Assist?</h2>
          <p className="text-xl text-gray-700 mb-8 leading-relaxed">
            Expunge Assist is a free step-by-step tool that helps people with past convictions in California write a declaration. It is one part of the expungement process.
          </p>
          <p className="text-lg text-gray-500 mb-12 italic">
            This free tool is provided by <span className="font-bold text-gray-700">Hack for LA</span>, a project under the nonprofit Civic Tech Structure. Expunge Assist is not a replacement for legal advice.
          </p>
          <button className="border-2 border-emerald-700 text-emerald-700 px-10 py-3 rounded-md font-bold hover:bg-emerald-50 transition-colors uppercase tracking-wider text-sm">
            About Us
          </button>
        </div>
      </section>

      {/* --- FEATURES --- */}
      <section className="py-20 bg-gray-50 border-y border-gray-100">
        <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row items-center gap-16">
          <div className="md:w-1/2 order-2 md:order-1">
            <div className="w-full aspect-video bg-white shadow-2xl rounded-xl border border-gray-200 overflow-hidden relative">
                <div className="absolute top-0 w-full h-8 bg-gray-100 border-b flex items-center px-4 space-x-2">
                    <div className="w-2 h-2 rounded-full bg-red-400"></div>
                    <div className="w-2 h-2 rounded-full bg-yellow-400"></div>
                    <div className="w-2 h-2 rounded-full bg-green-400"></div>
                </div>
                <div className="flex items-center justify-center h-full pt-8 text-gray-400 font-medium">
                    [Preview: Interactive Form UI]
                </div>
            </div>
          </div>
          <div className="md:w-1/2 order-1 md:order-2">
            <h2 className="text-3xl md:text-4xl font-bold text-emerald-900 mb-8 leading-snug">Making declaration writing less intimidating</h2>
            <ul className="space-y-6">
              {[
                "Questions guide the writing process",
                "Sections help keep writing organized",
                "Edit function gives you control"
              ].map((text, i) => (
                <li key={i} className="flex items-start">
                  <CheckCircle2 className="text-emerald-500 mt-1 mr-4 flex-shrink-0" size={24} />
                  <p className="text-xl text-gray-700 font-medium">{text}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* --- HOW IT WORKS (VERTICAL) --- */}
      <section className="py-24 bg-white">
        <div className="max-w-4xl mx-auto px-4">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold mb-4 tracking-tight">How it works</h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              We provide step-by-step guidance through the process of writing and downloading a declaration.
            </p>
          </div>
          
          <div className="flex flex-col gap-16 relative">
            {/* Desktop Vertical Line */}
            <div className="hidden md:block absolute left-8 top-8 bottom-8 w-0.5 bg-emerald-100 z-0"></div>

            {/* Steps */}
            {[
              { title: "Answer questions", desc: "Follow simple question prompts to know what and how much to say. The tool guides you through your personal history and the reasons for your request." },
              { title: "Preview and edit text", desc: "Preview what you've written and make any changes after each section and at the end. You have full control over the final wording of your declaration." },
              { title: "Download declaration", desc: "When you're happy with the declaration, download, copy, or email it to use in your application. We provide the final document in a format ready for court submission." }
            ].map((step, i) => (
              <div key={i} className="flex flex-col md:flex-row items-center md:items-start gap-8 md:gap-12 relative z-10">
                <div className="flex-shrink-0 w-16 h-16 bg-emerald-100 text-emerald-800 rounded-full flex items-center justify-center text-2xl font-black shadow-inner">
                  {i + 1}
                </div>
                <div className="text-center md:text-left">
                  <h3 className="text-2xl font-bold mb-3 text-emerald-900">{step.title}</h3>
                  <p className="text-lg text-gray-600 leading-relaxed">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* --- PRIVACY BANNER (CORRECTED) --- */}
      <section className="py-20 bg-emerald-900 text-white overflow-hidden relative">
        <div className="absolute top-0 right-0 opacity-10 transform translate-x-1/4 -translate-y-1/4 pointer-events-none">
            <Globe size={400} />
        </div>
        <div className="max-w-4xl mx-auto px-4 text-center relative z-10">
          <h2 className="text-3xl md:text-4xl font-bold mb-8">Your Privacy</h2>
          <p className="text-xl md:text-2xl opacity-90 mb-10 leading-relaxed font-light">
            Expunge Assist does not save your answers after you leave this website. Save your declaration before leaving, and protect it as you would anything personal.
          </p>
          <button className="text-lg font-bold border-b-2 border-white hover:text-emerald-200 hover:border-emerald-200 transition-all pb-1 uppercase tracking-widest">
            Read Privacy Policy
          </button>
        </div>
      </section>

      {/* --- FAQ SECTION --- */}
      <section className="py-24 bg-gray-50">
        <div className="max-w-3xl mx-auto px-4">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-16 tracking-tight">Frequently asked questions</h2>
          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div key={index} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <button 
                  onClick={() => toggleFaq(index)}
                  className="w-full flex justify-between items-center p-6 text-left font-bold text-gray-800 hover:bg-gray-50 transition-colors"
                >
                  <span className="pr-8">{faq.question}</span>
                  <div className={`transition-transform duration-300 ${activeFaq === index ? 'rotate-180' : ''}`}>
                    <ChevronDown className="text-emerald-700" />
                  </div>
                </button>
                <div className={`overflow-hidden transition-all duration-300 ease-in-out ${activeFaq === index ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'}`}>
                  <div className="p-6 pt-0 text-gray-600 border-t leading-relaxed text-lg">
                    {faq.answer}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="text-center mt-12">
            <button className="text-emerald-700 font-bold text-lg flex items-center justify-center mx-auto hover:underline group">
              View all FAQs 
              <ChevronDown size={20} className="ml-2 group-hover:translate-y-1 transition-transform" />
            </button>
          </div>
        </div>
      </section>

      {/* --- FOOTER --- */}
      <footer className="bg-white border-t py-16">
        <div className="max-w-7xl mx-auto px-4 text-gray-600">
          <div className="flex flex-col md:flex-row justify-between items-center gap-12">
            <div className="flex flex-wrap justify-center md:justify-start gap-x-10 gap-y-4 font-bold text-sm uppercase tracking-wider">
              <a href="#" className="hover:text-emerald-700 transition-colors">Privacy Policy</a>
              <a href="#" className="hover:text-emerald-700 transition-colors">Terms of Use</a>
              <a href="#" className="hover:text-emerald-700 transition-colors">Contact Us</a>
              <a href="#" className="hover:text-emerald-700 transition-colors">Credits</a>
            </div>
            
            <div className="flex flex-col items-center md:items-end">
              <div className="flex items-center text-gray-900 mb-3">
                <span className="font-black text-lg mr-2">Hack for LA</span>
                <ExternalLink size={18} />
              </div>
              <p className="text-sm font-medium">© 2026 Expunge Assist. All rights reserved.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HP2;