import React, { useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import BeaverIcon from './shared/components/BeaverIcon';

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, useGSAP);
}

const HeartIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
  </svg>
);

const HP = () => {
  const mainRef = useRef(null);
  const pinnedWrapper = useRef(null);
  const sceneRef = useRef(null);
  const finalSectionRef = useRef(null);

  const stackCards = [
    { id: 1, title: "This chatbot is designed to provide answers to your tenant rights questions", desc: "It is free, so feel free to ask away!" },
    { id: 2, title: "It uses Gemini 2.5", desc: "This is a chatbot, it does not provide legal advice, but it may have good advice" },
    { id: 3, title: "Legal", desc: "It draws on Oregon Tenant rights laws" },
    { id: 4, title: "Disclaimer", desc: "This section is for a disclaimer" },
  ];

  const heartsArray = Array.from({ length: 40 });

  useGSAP(() => {
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: pinnedWrapper.current,
        start: "top top",
        end: "+=10000", 
        scrub: 1.5,
        pin: true,
        anticipatePin: 1,
      }
    });

    // --- STAGE 1: Beaver Expansion & Header Transition ---
    tl.to(".user-cta-block", { 
      top: 0, y: 0, scale: 0.9,
      duration: 3, ease: "power2.inOut" 
    }, 0);

    // BEAVER FADE SPEED: Duration reduced by factor of 2.372 (4 / 2.372 = 1.686)
    tl.to(".main-beaver", { 
      x: 0, scale: 12, opacity: 0.02, z: -1200, 
      duration: 1.686, 
      ease: "power2.inOut" 
    }, 0);

    tl.to(".intro-glass-content", { scale: 2.5, z: 800, opacity: 0, duration: 2.5 }, 0.5);

    // --- STAGE 2: Purple Shift & Card Stack ---
    tl.to(mainRef.current, { backgroundColor: '#110521', duration: 3 }, 2);
    tl.from(".stack-card", { scale: 0.8, opacity: 0, z: -500, stagger: 0.2, duration: 1.5 }, 2.5);
    tl.to(".stack-card", { y: (i) => (i - 1.5) * 165, opacity: 1, duration: 2, ease: "power3.out" }, 3);

    // --- STAGE 3: Sidebar Shift ---
    tl.to(".stack-card", { x: "-32vw", scale: 0.82, rotationY: 25, opacity: 0.2, duration: 2.5, ease: "expo.inOut" }, 5);

    // --- STAGE 4: Narrative Highlights ---
    tl.from(".story-1", { x: 80, opacity: 0, duration: 2 }, 6);
    tl.to(".card-0, .card-1", { opacity: 1, scale: 0.95, borderColor: 'rgba(255, 255, 255, 0.6)', duration: 1.2 }, 6);
    tl.to(".story-1", { x: -30, opacity: 0, duration: 2 }, 8);
    tl.to(".card-0, .card-1", { opacity: 0.2, scale: 0.82, borderColor: 'rgba(255,255,255,0.08)', duration: 1 }, 8);

    tl.from(".story-2", { x: 80, opacity: 0, duration: 2 }, 8.5);
    tl.to(".card-2, .card-3", { opacity: 1, scale: 0.95, borderColor: 'rgba(255, 255, 255, 0.6)', duration: 1.2 }, 8.5);
    tl.to(".story-2", { x: -30, opacity: 0, duration: 2 }, 10.5);

    tl.to(".stack-card", { opacity: 0, x: "-50vw", duration: 1 }, 10.5);

    // Floating Hearts (Floats 2.372x slower)
    ScrollTrigger.create({
      trigger: finalSectionRef.current,
      start: "top center",
      onEnter: () => {
        gsap.to(".heart-particle", {
          y: -window.innerHeight,
          x: "random(-50, 50)",
          rotation: "random(-90, 90)",
          scale: "random(0.5, 1.5)",
          opacity: "random(0.5, 1)",
          duration: "random(9.5, 19)", 
          stagger: { amount: 3, repeat: -1 },
          ease: "sine.inOut",
          repeatRefresh: true
        });
      }
    });

    const handleMouseMove = (e) => {
      const { clientX, clientY } = e;
      const x = (clientX / window.innerWidth - 0.5) * 6;
      const y = (clientY / window.innerHeight - 0.5) * 6;
      gsap.to(sceneRef.current, { rotationY: x, rotationX: -y, duration: 1.5 });
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, { scope: mainRef });

  return (
    <div ref={mainRef} style={styles.pageContainer}>
      <style>{hoverStyles}</style>
      
      {/* Green CTA Block */}
      <div className="user-cta-block" style={styles.userBlockInitial}>
          <div className="flex-l justify-between mw8 center white pa4"
                style={{background: 'green', width: '100vw', borderRadius: '8px', display: "flex", justifyContent: "space-between", minHeight: "150px", alignItems: "center", paddingLeft: "200px", paddingRight: "200px"}}>
              <div className="w-50-l bt bw2 b--blue pt4 mr5-l mb5">
                <h4 className="f3 f2-ns fw9 lh-title mt0 mb4" style={{fontSize: "32px", color: "white", borderBottom: "2px solid white"}}>Free advice!</h4>
                <div className="f4 f3-ns fw7 link light-blue hover-white" onClick={() => window.scrollTo(0, 0)} style={{fontSize: "16px", color: "white", cursor: 'pointer'}}>
                  Chat with tenant rights bot.
                  <span className="fas fa-arrow-right f5 lh-solid pt1 pl2" aria-hidden="true"></span>
                </div>
              </div>
              <div className="w-50-l bt bw2 b--blue pt4 ml5-l mb5">
                <h4 className="f3 f2-ns fw9 lh-title mt0 mb4" style={{fontSize: "32px", color: "white", borderBottom: "2px solid white"}}>Draft a letter to your landlord.</h4>
                <div className="f4 f3-ns fw7 link light-blue hover-white" onClick={() => window.scrollTo(0, 0)} style={{fontSize: "16px", color: "white", cursor: 'pointer'}}>
                  Get started
                  <span className="fas fa-arrow-right f5 lh-solid pt1 pl2" aria-hidden="true"></span>
                </div>
              </div>
            </div>
      </div>

      <div ref={pinnedWrapper} style={styles.pinnedHeight}>
        <div ref={sceneRef} style={styles.scene}>
          <div className="main-beaver" style={styles.beaverWrapper}><BeaverIcon /></div>
          <div className="intro-glass-content" style={styles.layer}>
            <div style={styles.glassCard}>
              <div style={styles.heroLayout}><div style={{ width: '100px' }}></div><h3 style={styles.cardTitle}>Tenant First Aid</h3></div>
            </div>
          </div>
          {stackCards.map((card, i) => (
            <div key={card.id} className={`stack-card card-${i}`} style={styles.stackCard}>
              <div style={styles.cardInner}>
                <span style={styles.cardTag}>0{card.id}</span>
                <h4 style={styles.cardSmallTitle}>{card.title}</h4>
                <p style={styles.cardSmallDesc}>{card.desc}</p>
              </div>
            </div>
          ))}
          <div style={styles.narrativeContainer}>
            <div className="story-1" style={styles.storyBlock}>
              <h2 style={styles.narrativeHeader}>This chatbot is designed to answer questions regarding tenants rights in Oregon</h2>
              <p style={styles.narrativeText}>After you use the chatbot, or before, use the letter feature in the nav bar to draft a letter to your landlord.</p>
            </div>
            <div className="story-2" style={styles.storyBlock}>
              <h2 style={styles.narrativeHeader}>The tenants rights Beaver is used in this app to indicate that you are in Oregon. We hope to add other states soon. The beaver will be there! To help!</h2>
              <p style={styles.narrativeText}>This app is not legal advice. It is designed to help you understand your rights as a tenant in Oregon.</p>
            </div>
          </div>
        </div>
      </div>

      <section ref={finalSectionRef} style={styles.finalSection}>
        <div style={styles.heartsContainer}>
          {heartsArray.map((_, i) => (
            <div key={i} className="heart-particle" style={{...styles.heart, left: `${Math.random() * 100}%`, color: Math.random() > 0.5 ? '#74c69d' : '#bc6ff1'}}>
              <HeartIcon />
            </div>
          ))}
        </div>
        <div style={styles.finalContent}>
          <h1 className="blue-hover-text" style={styles.giantHeading}>Write us <span>an Email</span></h1>
          <button style={styles.primaryBtn}>or use the chat bot. It's also in the upper left.</button>
        </div>
      </section>
    </div>
  );
};

const hoverStyles = `
  .blue-hover-text { transition: all 0.5s ease; cursor: default; }
  .blue-hover-text:hover { color: #00d4ff !important; text-shadow: 0 0 30px rgba(0, 212, 255, 0.6); transform: scale(1.05); }
  .blue-hover-text:hover span { color: #00d4ff; }
`;

const styles = {
  pageContainer: { backgroundColor: '#081c15', width: '100vw', overflowX: 'hidden', transition: 'background-color 1.5s ease' },
  userBlockInitial: { position: 'fixed', top: '65%', left: '50%', transform: 'translateX(-50%)', width: '100vw', zIndex: 1000, pointerEvents: 'auto' },
  pinnedHeight: { height: '100vh', width: '100%' },
  scene: { height: '100vh', width: '100%', position: 'relative', transformStyle: 'preserve-3d', display: 'flex', alignItems: 'center', justifyContent: 'center', perspective: '2000px' },
  beaverWrapper: { position: 'absolute', width: '80px', height: '80px', zIndex: 10, transform: 'translateX(-160px)', pointerEvents: 'none' },
  layer: { position: 'absolute', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none', transformStyle: 'preserve-3d' },
  heroLayout: { display: 'flex', alignItems: 'center', gap: '20px' },
  glassCard: { padding: '3rem', background: 'rgba(255, 255, 255, 0.02)', backdropFilter: 'blur(30px)', borderRadius: '40px', border: '1.5px solid rgba(255, 255, 255, 0.1)', textAlign: 'center', width: 'min(90%, 550px)', color: 'white' },
  cardTitle: { fontSize: '2.5rem', margin: 0 },
  stackCard: { position: 'absolute', width: '300px', padding: '1.5rem', background: 'rgba(255, 255, 255, 0.03)', backdropFilter: 'blur(20px)', borderRadius: '16px', color: 'white', border: '1px solid rgba(255,255,255,0.08)', zIndex: 10, left: 'calc(50% - 150px)', top: 'calc(50% - 100px)', minHeight: '210px' },
  cardInner: { textAlign: 'left' },
  cardTag: { fontSize: '0.7rem', color: '#74c69d', fontWeight: 'bold' },
  cardSmallTitle: { fontSize: '1rem', margin: '8px 0', lineHeight: '1.4' },
  cardSmallDesc: { fontSize: '0.75rem', opacity: 0.5 },
  narrativeContainer: { position: 'absolute', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: '10%', pointerEvents: 'none' },
  storyBlock: { position: 'absolute', textAlign: 'left', maxWidth: '550px', color: 'white' },
  narrativeHeader: { fontSize: '3rem', margin: '0 0 1.2rem 0', fontWeight: '800', lineHeight: '1.1' },
  narrativeText: { fontSize: '1.2rem', opacity: 0.7, lineHeight: '1.7' },
  finalSection: { height: '100vh', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 100, overflow: 'hidden' },
  heartsContainer: { position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' },
  heart: { position: 'absolute', bottom: '-50px', opacity: 0 },
  finalContent: { textAlign: 'center', zIndex: 10 },
  giantHeading: { fontSize: 'clamp(3rem, 10vw, 8rem)', fontWeight: '900', color: 'white', margin: 0 },
  primaryBtn: { marginTop: '2.5rem', padding: '1.2rem 4rem', borderRadius: '100px', border: 'none', backgroundColor: '#74c69d', color: '#081c15', fontWeight: 'bold', cursor: 'pointer', fontSize: '1.1rem' }
};

export default HP;