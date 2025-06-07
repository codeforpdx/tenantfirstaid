import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Chat from "./Chat.tsx";
import AboutPage from "./AboutPage.tsx";
import SessionContextProvider from "./contexts/SessionContext.tsx";
import Navbar from "./pages/Chat/components/Navbar.tsx";

export default function App() {
  return (
    <SessionContextProvider>
      <Router>
        <Navbar />
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </Router>
    </SessionContextProvider>
  );
}
