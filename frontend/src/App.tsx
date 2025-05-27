import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Chat from "./Chat.tsx";
import PromptEditor from "./PromptEditor.tsx";
import AboutPage from "./AboutPage.tsx";
import SessionContextProvider from "./contexts/SessionContext.tsx";

export default function App() {
  return (
    <SessionContextProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/prompt" element={<PromptEditor />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </Router>
    </SessionContextProvider>
  );
}
