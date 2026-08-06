import { lazy, Suspense } from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router";
import Navbar from "./shared/components/Navbar/Navbar";
import RegionNotice from "./shared/components/RegionNotice";
import Chat from "./Chat";
import LoadingPage from "./pages/LoadingPage";
import PageLayout from "./layouts/PageLayout";
import HomePage from "./pages/HomePage/HomePage";

// Lazy-loading for less frequented pages
const About = lazy(() => import("./About"));
const Disclaimer = lazy(() => import("./Disclaimer"));
const PrivacyPolicy = lazy(() => import("./PrivacyPolicy"));
const Referrals = lazy(() => import("./Referrals"));
const Letter = lazy(() => import("./Letter"));

export default function App() {
  return (
    <Router>
      <Navbar />
      <RegionNotice />
      <PageLayout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route
            path="/*"
            element={
              <Suspense fallback={<LoadingPage />}>
                <Routes>
                  <Route path="/chat/:state?/:city?" element={<Chat />} />
                  <Route path="/letter/:state?/:city?" element={<Letter />} />
                  <Route path="/about" element={<About />} />
                  <Route path="/disclaimer" element={<Disclaimer />} />
                  <Route path="/privacy-policy" element={<PrivacyPolicy />} />
                  <Route path="/referrals" element={<Referrals />} />
                </Routes>
              </Suspense>
            }
          />
        </Routes>
      </PageLayout>
      <footer className="fixed bottom-0 left-0 w-full h-(--footer-height) bg-paper-background border-t border-gray-light flex items-center justify-end px-4 text-xs text-gray-dark z-40">
        <span>
          &copy; {new Date().getFullYear()} Tenant First Aid
          <span className="mx-2">|</span>
          UI Version {__APP_VERSION__}
        </span>
      </footer>
    </Router>
  );
}
