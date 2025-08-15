import { useRef, useState } from "react";
import type { IMessage } from "../../../hooks/useMessages";

interface Props {
  setMessages: React.Dispatch<React.SetStateAction<IMessage[]>>;
  isLoading: boolean;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function DocumentUpload({
  setMessages,
  isLoading,
  setIsLoading,
}: Props) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedTypes = [
        "image/png",
        "image/jpeg",
        "image/jpg",
        "application/pdf",
      ];
      if (!allowedTypes.includes(file.type)) {
        alert("Please select a PNG, JPG, JPEG, or PDF file.");
        return;
      }

      // Validate file size (10MB limit)
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (file.size > maxSize) {
        alert("File size must be less than 10MB.");
        return;
      }

      setSelectedFile(file);
    }
  };

  const handleUploadAndAnalyze = async () => {
    if (!selectedFile) return;

    const userMessageId = Date.now().toString();
    const botMessageId = (Date.now() + 1).toString();

    setIsLoading(true);

    // Add user message about document upload
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: `I've uploaded a document: ${selectedFile.name}`,
        messageId: userMessageId,
      },
    ]);

    // Add empty bot message that will be updated
    setMessages((prev) => [
      ...prev,
      {
        role: "model",
        content: "",
        messageId: botMessageId,
      },
    ]);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        fullText += chunk;

        // Update only the bot's message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.messageId === botMessageId
              ? { ...msg, content: fullText }
              : msg,
          ),
        );
      }
    } catch (error) {
      console.error("Upload error:", error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.messageId === botMessageId
            ? {
                ...msg,
                content:
                  "Sorry, I encountered an error while analyzing your document. Please try again.",
              }
            : msg,
        ),
      );
    } finally {
      setIsLoading(false);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="flex flex-col gap-2 mt-4 mx-auto max-w-[700px]">
      <div className="flex gap-2 items-center">
        <input
          ref={fileInputRef}
          type="file"
          accept=".png,.jpg,.jpeg,.pdf"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isLoading}
        />
        <button
          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors cursor-pointer"
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
        >
          Choose Document
        </button>
        {selectedFile && (
          <span className="text-sm text-gray-600 truncate max-w-xs">
            {selectedFile.name}
          </span>
        )}
      </div>

      {selectedFile && (
        <div className="flex gap-2 justify-center">
          <button
            className="px-4 py-2 bg-[#1F584F] hover:bg-[#4F8B82] text-white rounded-md cursor-pointer transition-colors"
            onClick={handleUploadAndAnalyze}
            disabled={isLoading}
          >
            {isLoading ? "Analyzing..." : "Upload & Analyze"}
          </button>
          <button
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors cursor-pointer"
            onClick={() => {
              setSelectedFile(null);
              if (fileInputRef.current) {
                fileInputRef.current.value = "";
              }
            }}
            disabled={isLoading}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}