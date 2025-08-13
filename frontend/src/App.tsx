import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Chat from "./Chat";
import About from "./About";
import Navbar from "./pages/Chat/components/Navbar";
import Disclaimer from "./Disclaimer";
import PrivacyPolicy from "./PrivacyPolicy";

export default function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/about" element={<About />} />
        <Route path="/disclaimer" element={<Disclaimer />} />
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
      </Routes>
    </Router>
  );
}
