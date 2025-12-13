import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Chat from "./Chat";
import About from "./About";
import Navbar from "./shared/components/Navbar/Navbar";
import Disclaimer from "./Disclaimer";
import PrivacyPolicy from "./PrivacyPolicy";
import Letter from "./Letter";

export default function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/letter" element={<Letter />} />
        <Route path="/letter/:org/:loc?" element={<Letter />} />
        <Route path="/about" element={<About />} />
        <Route path="/disclaimer" element={<Disclaimer />} />
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
      </Routes>
    </Router>
  );
}
