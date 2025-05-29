import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Chat from "./Chat.tsx";
import Feedback from "./Feedback.tsx";
import AboutPage from "./AboutPage.tsx";
import SessionContextProvider from "./contexts/SessionContext.tsx";

export default function App() {
  return (
    <SessionContextProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </Router>
    </SessionContextProvider>
  );
}
