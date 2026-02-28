import { lazy, Suspense } from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Navbar from "./shared/components/Navbar/Navbar";
import Chat from "./Chat";
import LoadingPage from "./pages/LoadingPage";
import PageLayout from "./layouts/PageLayout";

// Lazy-loading for less frequented pages
const About = lazy(() => import("./About"));
const Disclaimer = lazy(() => import("./Disclaimer"));
const PrivacyPolicy = lazy(() => import("./PrivacyPolicy"));
const Letter = lazy(() => import("./Letter"));

export default function App() {
  return (
    <Router>
      <Navbar />
      <PageLayout>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route
            path="/*"
            element={
              <Suspense fallback={<LoadingPage />}>
                <Routes>
                  <Route path="/letter" element={<Letter />} />
                  <Route path="/letter/:org/:loc?" element={<Letter />} />
                  <Route path="/about" element={<About />} />
                  <Route path="/disclaimer" element={<Disclaimer />} />
                  <Route path="/privacy-policy" element={<PrivacyPolicy />} />
                </Routes>
              </Suspense>
            }
          />
        </Routes>
        <footer className="hidden sm:block fixed bottom-4 right-4 text-xs">
          UI Version {__APP_VERSION__}
        </footer>
      </PageLayout>
    </Router>
  );
}
