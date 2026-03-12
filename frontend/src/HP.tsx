import React, { useRef, useState } from 'react';
import BeaverIcon from '../src/shared/components/BeaverIcon';
import TenantFirstAidLogo from "../src/shared/components/TenantFirstAidLogo";
import LetterTemplate from '../public/LetterTemplate.png';
import ChatExample from '../public/ChatExample.png';
import LetterExample from '../public/LetterExample.png';
import { REFERENCED_LAW_LIST } from './shared/constants/constants';
import HPFeedbackForm from './HPFeedbackForm';

// -----------------------------------------------------------------------------
// ICONS
// -----------------------------------------------------------------------------

const AirVentIcon = ({ size = 24, color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 12H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 8h12"/><path d="M18.3 17.7a2.5 2.5 0 0 1-3.16 3.83 2.53 2.53 0 0 1-1.14-2V12"/><path d="M6.6 15.6A2 2 0 1 0 10 17v-5"/></svg>
);

const ChartIcon = ({ size = 24, color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
);

const ActivityIcon = ({ size = 24, color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
);

const CheckCircle = ({color="#10B981"}) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
);

const XCircle = ({color="#EF4444"}) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
);

const ChevronRight = ({size=32, color="currentColor"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
);

// -----------------------------------------------------------------------------
// MAIN COMPONENT
// -----------------------------------------------------------------------------

const HP = () => {
  const mainRef = useRef(null);
  const [activeLetterIndex, setActiveLetterIndex] = useState(0);
  const letterImages = [LetterTemplate, ChatExample, LetterExample];

  const handleNextLetter = () => {
    setActiveLetterIndex((prev) => (prev + 1) % letterImages.length);
  };

  const roadmapItems = [
    { phase: "", title: "Ask questions", desc: "Chat with Brainy about your housing issues.", status: "complete" },
    { phase: "", title: "Write letters", desc: "Brainy can help draft letters to your landlord.", status: "active" },
  ];

  // --- HELPER FUNCTIONS ---

  const getCardStyle = (index: number) => {
    const position = (index - activeLetterIndex + letterImages.length) % letterImages.length;
    
    const baseStyle: React.CSSProperties = {
      position: 'absolute',
      top: '10px', 
      left: 0,
      width: '100%',
      height: 'auto',
      transition: 'all 1.27s cubic-bezier(0.34, 1.56, 0.64, 1)',
      cursor: 'pointer',
      boxShadow: '0 25px 50px rgba(0,0,0,0.4)', 
      border: '1px solid rgba(230, 213, 184, 0.3)', 
      backgroundColor: 'rgba(230, 213, 184, 0.7)', 
      backdropFilter: 'blur(12px)',
      padding: '15px',
      borderRadius: '16px',
      boxSizing: 'border-box',
    };

    if (position === 0) {
      return { ...baseStyle, zIndex: 10, transform: 'scale(1) translateX(0) translateY(0) rotate(0deg)', opacity: 1 };
    } else if (position === 1) {
      return { ...baseStyle, zIndex: 9, transform: 'scale(0.98) translateX(-20px) translateY(-25px) rotate(-2deg)', opacity: 0.8 };
    } else {
      return { ...baseStyle, zIndex: 8, transform: 'scale(0.96) translateX(-40px) translateY(-50px) rotate(-4deg)', opacity: 0.6 };
    }
  };

  return (
    <>
    <div ref={mainRef} style={styles.pageContainer}>
      <style>{`
        html, body { margin: 0; padding: 0; overflow-x: hidden; width: 100%; background-color: #022C22; }
        
        .stack-height { height: 550px; } 

        @media (max-width: 550px) {
          #compare { padding: 0px 0px !important; }
        } 

        @media (max-width: 950px) {
          .responsive-flex { flex-direction: column !important; }
          .hero-text { font-size: 2.5rem !important; }
          .hide-mobile { display: none !important; }
          .mobile-center { text-align: center !important; }
          .rag-steps-responsive { flex-direction: column !important; }
          .roadmap-layout { flex-direction: column-reverse !important; gap: 80px !important; }
          
          .carousel-container { 
            padding-right: 0px !important; 
            margin-top: 60px; 
            width: 100vw !important; 
            margin-left: -20px !important; 
          }
          .arrow-button-mobile { right: 20px !important; top: 50% !important; }
          .stack-height { height: 500px; } 
          
          .mobile-scroll-x { overflow-x: auto !important; padding: 1.5rem !important; padding-left: 0 !important; }
          .mobile-min-width { min-width: 700px !important; }
          
          .comparison-grid > div:nth-child(4n+1) {
            position: sticky;
            left: 0;
            z-index: 10;
            border-right: 1px solid rgba(230, 213, 184, 0.2);
            background-color: #0E362D !important; 
          }
          .comparison-grid > div:nth-child(1) {
             background-color: #064E3B !important;
          }
        }
        
        .hover-arrow:hover { 
            transform: translateY(-50%) scale(1.15); 
            background-color: #10B981 !important; 
            color: #022C22 !important; 
            border-color: #10B981 !important; 
        }
        
        ::selection { background: #10B981; color: #FFFFFF; }
        
        .btn-hover:hover { transform: scale(1.02758); }
      `}</style>

      <div style={styles.massiveBackdrop}><TenantFirstAidLogo /></div>
      
      <div style={styles.leftBar} className="hide-mobile"></div>
      <div style={styles.rightBar} className="hide-mobile"></div>
      
      <section style={styles.heroSection}>
        <div style={styles.glassCardHero}>
          <div style={styles.heroLayout}>
            <div style={styles.beaverBox}><BeaverIcon /></div>
            <h1 className="hero-text" style={styles.cardTitleHero}>Tenant First Aid</h1>
          </div>
          <p style={{marginTop: "25px", color: '#F4F4F2', fontSize: '16px', lineHeight: '1.8', fontWeight: '500'}}>
          </p>
        </div>
      </section>

      <div className="cta-trigger" style={styles.ctaWrapper}>
          <div className="mw8 center white responsive-flex" style={styles.originalCtaFlex}>
              <div style={styles.ctaHalf}>
                <div style={styles.ctaLink}>
                  <a href="/chat" style={{textDecoration: "none"}}><h4 style={styles.ctaHeading}>Chat with Brainy<span style={{paddingLeft: '10px'}}>→</span></h4></a>
                </div>
              </div>
              <div style={styles.ctaHalf}>
                <div style={styles.ctaLink}>
                  <a href="/letter" style={{textDecoration: "none"}}><h4 style={styles.ctaHeading}>Draft a letter<span style={{paddingLeft: '10px'}}>→</span></h4></a>
                </div>
              </div>
          </div>
      </div>

      <section style={styles.centralSection}>
        <div className="roadmap-layout" style={styles.splitLayout}>
            
            <div style={{flex: 1}}>
                <h3 style={{...styles.narrativeHeader, fontSize: '32px', marginBottom: '40px', color: '#F4F4F2'}}>How to use Brainy</h3>
                <div style={styles.roadmapContainer}>
                  {roadmapItems.map((item, i) => (
                    <div key={i} style={styles.roadmapItem}>
                      <div style={styles.roadmapMarker}>
                        <div style={{...styles.markerDot, backgroundColor: item.status === 'active' ? '#10B981' : item.status === 'complete' ? '#34D399' : '#064E3B'}}></div>
                        {i !== roadmapItems.length - 1 && <div style={styles.markerLine}></div>}
                      </div>
                      <div style={styles.roadmapContent}>
                        <span style={styles.roadmapPhase}>{item.phase}</span>
                        <h4 style={styles.roadmapTitle}>{item.title}</h4>
                        <p style={styles.roadmapDesc}>{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
            </div>

            {/* Carousel Column */}
            <div className="carousel-container" style={{flex: 1.5, position: 'relative'}}>
                <div style={styles.stackWrapper}>
                  <div className="stack-height" style={{ ...styles.stackInternalRelative, height: 'auto' }}>
                    <img src={letterImages[0]} alt="" aria-hidden="true" style={{ width: '100%', height: 'auto', visibility: 'hidden', display: 'block' }} />
                    {letterImages.map((img, index) => (
                      <div key={index} style={getCardStyle(index)} onClick={handleNextLetter}>
                         <img src={img} alt="Letter" style={{width: '100%', height: 'auto', display: 'block'}} />
                      </div>
                    ))}
                  </div>
                  
                  <div 
                    className="hover-arrow arrow-button-mobile"
                    onClick={handleNextLetter} 
                    style={styles.arrowButton}
                  >
                    <ChevronRight color="#022C22" />
                  </div>
                </div>

                <p style={styles.imageCaption}>Example outputs generated by Brainy</p>
            </div>
        </div>
      </section>

      <section id="how-it-works" style={styles.centralSection}>
        <div style={styles.ragContainer}>
          <h2 style={{...styles.narrativeHeader, textAlign: 'center', marginBottom: '20px', color: '#F4F4F2'}}>Why ask Brainy?</h2>
          <p style={{...styles.ragIntroText, textAlign: 'center', marginTop: '10px', marginBottom: '50px'}}>
            Brainy uses a <span style={styles.blueMono}>Retrieval-Augmented Generation</span> approach to look up information from curated legal sources
          </p>
          <div className="rag-steps-responsive" style={styles.ragStepsHorizontal}>
                <div style={styles.ragStepCard}>
                  <h4 style={styles.ragStepTitle}><AirVentIcon size={24} color="#10B981" /> Retrieve</h4>
                  <p style={styles.ragStepDesc}>Brainy retrieves the most relevant information about Oregon housing law, including</p>
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
                <div style={styles.ragStepCard}>
                  <h4 style={styles.ragStepTitle}><ChartIcon size={24} color="#10B981" /> Augment</h4>
                  <p style={styles.ragStepDesc}>Brainy combines what it finds with the questions the user asks.</p>
                </div>
                <div style={styles.ragStepCard}>
                  <h4 style={styles.ragStepTitle}><ActivityIcon size={24} color="#10B981" /> Generate</h4>
                  <p style={styles.ragStepDesc}>Brainy writes a clear, concise answer.</p>
                </div>
          </div>
        </div>
      </section>

      <section id="compare" style={styles.compareSection}>
        <h2 style={{...styles.narrativeHeader, textAlign: 'center', paddingLeft: '10vw', paddingRight: '10vw', marginBottom: '20px', color: '#F4F4F2'}}>Which approach is right for you?</h2>
        <div className="mobile-scroll-x" style={styles.compareCard}>
          <div className="mobile-min-width comparison-grid" style={styles.tableGrid}>
            <div style={styles.tableHeader}></div>
            <div style={styles.tableHeaderHighlight}>Tenant First Aid</div>
            <div style={styles.tableHeader}>Traditional Legal Aid</div>
            <div style={styles.tableHeader}>ChatGPT</div>
            
            <div style={styles.tableCell}>Always available</div>
            <div style={styles.tableCellHighlight}><CheckCircle /></div>
            <div style={styles.tableCell}><XCircle /></div>
            <div style={styles.tableCell}><CheckCircle /></div>

            <div style={styles.tableCell}>Always free</div>
            <div style={{...styles.tableCellHighlight, color: 'rgb(66, 255, 188)'}}><CheckCircle /></div>
            <div style={styles.tableCell}><XCircle /></div>
            <div style={styles.tableCell}><XCircle /></div>
            
            <div style={styles.tableCell}>No eligibility requirements</div>
            <div style={styles.tableCellHighlight}><CheckCircle /></div>
            <div style={styles.tableCell}><XCircle /></div>
            <div style={styles.tableCell}><CheckCircle /></div>

            <div style={styles.tableCell}>Provides legal advice</div>
            <div style={styles.tableCellHighlight}><XCircle /></div>
            <div style={styles.tableCell}><CheckCircle /></div>
            <div style={styles.tableCell}><XCircle /></div>

            <div style={styles.tableCell}>Only references relevent laws</div>
            <div style={styles.tableCellHighlight}><CheckCircle /></div>
            <div style={styles.tableCell}><CheckCircle /></div>
            <div style={styles.tableCell}><XCircle /></div>
            
            <div style={styles.tableCell}>Direct advocacy with court/landlords</div>
            <div style={styles.tableCellHighlight}><XCircle /></div>
            <div style={styles.tableCell}><CheckCircle /></div>
            <div style={styles.tableCell}><XCircle /></div>
          </div>
        </div>
      </section>

      <section style={{...styles.centralSection, textAlign: 'center', marginBottom: '80px'}}>
        <div>
          <a href="/privacy-policy" style={{color: '#10B981', fontSize: '1.2rem', textDecoration: 'underline', cursor: 'pointer', fontWeight: 'bold'}}>
            Privacy Policy
          </a>
          <p style={{marginTop: '15px', color: '#F4F4F2', opacity: 0.8, fontSize: '1rem'}}>
            We don't store any of the information you input either in the session or on any servers
          </p>
        </div>
      </section>

      <section style={{...styles.centralSection, textAlign: 'center', marginBottom: '80px'}}>
        <div>
          <a href="/disclaimer" style={{color: '#10B981', fontSize: '1.2rem', textDecoration: 'underline', cursor: 'pointer', fontWeight: 'bold'}}>
            Disclaimer
          </a>
          <p style={{color: '#F4F4F2', opacity: 0.8, fontSize: '1rem', maxWidth: '800px', margin: '0 auto', lineHeight: '1.6'}}>
            The information provided by this chatbot is general information only and does not constitute legal advice. While Tenant First Aid strives to keep the content accurate and up to date, completeness and accuracy is not guaranteed. If you have a specific legal issue or question, consider contacting a qualified attorney or a local legal aid clinic for personalized assistance. For questions related to Tenant First Aid, contact <a href="mailto:michael@qiu-qiulaw.com" style={{color: '#10B981'}}>michael@qiu-qiulaw.com</a>.
          </p>
        </div>
      </section>

      <section style={styles.centralSection}>
        <div style={styles.glassCardFull}>
          <h2 style={styles.narrativeHeader}>Who We Are</h2>
          <p style={styles.narrativeText}>
            <strong>Tenant First Aid</strong> is a volunteer-built program by <a href="https://www.codepdx.org/" style={{color: '#10B981'}}>Code PDX</a> and <a href="mailto:michael@qiu-qiulaw.com" style={{color: '#10B981'}}>Qiu Qiu Law</a>. 
          </p>
        </div>
      </section>

      <section className="final-section" style={styles.finalSection}>
        <div style={styles.finalContent}>
          <h1 className="blue-hover-text" style={styles.giantHeading}>Get in touch</h1>
        </div>
      </section>

      <HPFeedbackForm nameValue="" subjectValue="" feedbackValue="" />
    </div>
    </>
  );
};

// -----------------------------------------------------------------------------
// STYLES
// -----------------------------------------------------------------------------

const styles = {
  pageContainer: { 
    backgroundColor: '#022C22', 
    width: '100%', 
    overflowX: 'hidden', 
    position: 'relative', 
    color: '#F4F4F2' 
  } as const,
  
  massiveBackdrop: { position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '150vw', height: 'auto', opacity: 0.05, zIndex: 0, pointerEvents: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10B981' },
  leftBar: { position: 'fixed', left: 0, top: 0, width: '12px', height: '100vh', backgroundColor: '#064E3B', zIndex: 1, opacity: 0.8, borderRight: '1px solid rgb(230, 213, 184)', pointerEvents: 'none' },
  rightBar: { position: 'fixed', right: 0, top: 0, width: '12px', height: '100vh', backgroundColor: '#064E3B', zIndex: 1, opacity: 0.8, borderLeft: '1px solid rgb(230, 213, 184)', pointerEvents: 'none' },
  
  heroSection: { minHeight: '56vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', position: 'relative', zIndex: 2 }, 
  
  glassCardHero: { 
    padding: '14px', 
    backdropFilter: 'blur(16px)', 
    width: '425px', 
    boxShadow: '0 8px 32px rgba(0,0,0,0.2)', 
    borderRadius: '24px' 
  }, 
  heroLayout: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '7.5px', flexWrap: 'wrap' }, 
  beaverBox: { width: '90px', height: '90px', display: 'flex', alignItems: 'center' }, 
  cardTitleHero: { fontSize: '32px', margin: 0, fontWeight: '900', color: '#F4F4F2', textShadow: 'none' }, 
  
  ctaWrapper: { 
    width: '100%', 
    background: 'rgba(230, 213, 184, 0.1)', 
    backdropFilter: 'blur(16px)', 
    position: 'relative', 
    zIndex: 2, 
    padding: '4rem 0', 
    borderTop: '1px solid rgba(230, 213, 184, 0.2)', 
    borderBottom: '1px solid rgba(230, 213, 184, 0.2)' 
  }, 
  originalCtaFlex: { display: "flex", justifyContent: "center", gap: "60px", maxWidth: '1200px', margin: '0 auto' }, 
  ctaHalf: { flex: 1, textAlign: 'center' }, 
  ctaHeading: { fontSize: "32px", color: "#F4F4F2", borderBottom: "2px solid #10B981", paddingBottom: "15px", fontWeight: '700' }, 
  ctaLink: { cursor: 'pointer', marginTop: '20px', color: "#10B981", fontWeight: '600' }, 
  
  compareSection: { maxWidth: '1100px', margin: '80px auto', padding: '0 20px', position: 'relative', zIndex: 2 },
  compareCard: { 
    background: 'rgba(230, 213, 184, 0.1)', 
    backdropFilter: 'blur(16px)', 
    border: '1px solid rgba(230, 213, 184, 0.2)', 
    padding: '3rem', 
    boxShadow: '0 15px 40px rgba(0,0,0,0.2)', 
    borderRadius: '24px',
    overflow: 'hidden'
  },
  tableGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1px', backgroundColor: 'rgba(230, 213, 184, 0.1)' }, 
  tableHeader: { padding: '20px', fontWeight: 'bold', backgroundColor: 'rgba(6, 78, 59, 0.8)', color: '#F4F4F2', textAlign: 'center' },
  tableHeaderHighlight: { padding: '20px', fontWeight: 'bold', backgroundColor: 'rgba(6, 78, 59, 0.8)', color: '#F4F4F2', textAlign: 'center' }, 
  tableCell: { padding: '20px', backgroundColor: 'rgba(230, 213, 184, 0.05)', color: '#F4F4F2', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '500' },
  tableCellHighlight: { padding: '20px', backgroundColor: 'rgba(230, 213, 184, 0.05)', color: '#F4F4F2', textAlign: 'center', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center' },

  centralSection: { maxWidth: '1200px', margin: '80px auto', padding: '0 20px', position: 'relative', zIndex: 2 },
  splitLayout: { display: 'flex', gap: '100px', alignItems: 'flex-start' },
  
  roadmapContainer: { display: 'flex', flexDirection: 'column' },
  roadmapItem: { display: 'flex', gap: '30px'},
  roadmapMarker: { display: 'flex', flexDirection: 'column', alignItems: 'center', width: '30px' },
  markerDot: { width: '18px', height: '18px', borderRadius: '50%', border: '2px solid #10B981', zIndex: 2 },
  markerLine: { width: '2px', flex: 1, backgroundColor: 'rgba(255,255,255,0.2)' },
  roadmapContent: { flex: 1, paddingBottom: '40px' },
  roadmapPhase: { fontSize: '0.9rem', color: '#10B981', fontWeight: 'bold', letterSpacing: '1px' },
  roadmapTitle: { fontSize: '1.6rem', margin: '8px 0', color: '#F4F4F2' },
  roadmapDesc: { opacity: 0.9, lineHeight: '1.6', color: '#F4F4F2' },
  
  stackWrapper: { width: '100%', position: 'relative', overflow: 'visible' },
  stackInternalRelative: { position: 'relative', width: '100%', overflow: 'visible' }, 
  arrowButton: { position: 'absolute', right: '0px', top: '50%', transform: 'translateY(-50%)', background: '#E6D5B8', border: '2px solid #022C22', borderRadius: '50%', width: '64px', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', transition: 'all 0.5s ease', zIndex: 30, boxShadow: '0 8px 20px rgba(0,0,0,0.5)' },
  imageCaption: { textAlign: 'center', color: '#10B981', marginTop: '36px', fontSize: '1rem', fontStyle: 'italic', fontWeight: '700', width: '100%', display: 'block' }, 

  ragContainer: { width: '100%' }, 
  ragIntroText: { fontSize: '1.4rem', color: '#34D399', fontWeight: '600' }, 
  blueMono: { color: '#E6D5B8', fontWeight: 'bold', textDecoration: 'underline', textDecorationColor: '#10B981' }, 
  ragStepsHorizontal: { display: 'flex', gap: '40px', marginTop: '50px' },
  ragStepCard: { 
    flex: 1, 
    backgroundColor: 'rgba(230, 213, 184, 0.1)', 
    backdropFilter: 'blur(16px)', 
    padding: '2rem', 
    border: '1px solid rgba(230, 213, 184, 0.2)', 
    borderRadius: '24px', 
    boxShadow: '0 10px 25px rgba(0,0,0,0.2)' 
  }, 
  ragStepTitle: { fontSize: '1.3rem', fontWeight: 'bold', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '1rem', color: '#F4F4F2' }, 
  ragStepDesc: { fontSize: '1rem', opacity: 1, color: '#F4F4F2', lineHeight: '1.6' }, 
  
  narrativeHeader: { fontSize: '36px', fontWeight: '800', color: '#F4F4F2', marginBottom: '20px' }, 
  narrativeText: { fontSize: '1.3rem', opacity: 1, lineHeight: '1.9', color: '#F4F4F2', fontWeight: '400' }, 
  glassCardFull: { 
    padding: '4rem', 
    background: 'rgba(230, 213, 184, 0.1)', 
    backdropFilter: 'blur(16px)', 
    border: '1px solid rgba(230, 213, 184, 0.2)', 
    textAlign: 'center', 
    borderRadius: '24px', 
    boxShadow: '0 15px 40px rgba(0,0,0,0.2)' 
  },
  
  finalSection: { height: '16vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }, 
  finalContent: { textAlign: 'center', zIndex: 3 }, 
  giantHeading: { fontSize: 'clamp(2.6rem, 10vw, 2.6rem)', fontWeight: '900', color: '#F4F4F2' }, 
  
  formSection: { display: 'flex', justifyContent: 'center', paddingBottom: '100px', position: 'relative', zIndex: 3 },
  contactForm: { display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', maxWidth: '600px', padding: '0 20px' },
  formInput: { padding: '16px', borderRadius: '12px', border: '1px solid rgba(230, 213, 184, 0.2)', backgroundColor: 'rgba(230, 213, 184, 0.05)', color: '#F4F4F2', fontSize: '1rem', outline: 'none', transition: 'border-color 0.3s ease' },
  formTextarea: { padding: '16px', borderRadius: '12px', border: '1px solid rgba(230, 213, 184, 0.2)', backgroundColor: 'rgba(230, 213, 184, 0.05)', color: '#F4F4F2', fontSize: '1rem', outline: 'none', minHeight: '160px', resize: 'vertical', transition: 'border-color 0.3s ease' },
  formSubmit: { padding: '16px', backgroundColor: 'rgba(230, 213, 184, 0.7)', color: 'rgb(0, 255, 143)', fontWeight: 'bold', fontSize: '1.2rem', border: 'none', borderRadius: '12px', cursor: 'pointer', transition: 'transform 0.2s ease, box-shadow 0.2s ease', boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)' }
} as const;

export default HP;