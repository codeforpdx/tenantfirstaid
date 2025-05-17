import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Chat from "./Chat.tsx";
import Feedback from "./Feedback.tsx";
import PromptEditor from "./PromptEditor.tsx";
import AboutPage from "./AboutPage.tsx"

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/feedback" element={<Feedback />} />
        <Route path="/prompt" element={<PromptEditor />} />
        <Route path="/about" element={<AboutPage />} />
      </Routes>
    </Router>
  );
}
