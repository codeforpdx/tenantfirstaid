export default async function sendHPFeedback(
  name: string,
  subject: string,
  feedback: string,
): Promise<{ success: boolean; message?: string }> {
  try {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("subject", subject);
    formData.append("feedback", feedback);

    const response = await fetch("/api/feedback", {
      method: "POST",
      body: formData,
    });

    // Check if the server responded with an error code (e.g., 400, 500)
    if (!response.ok) {
      throw new Error(`Server responded with status: ${response.status}`);
    }

    return { success: true };
  } catch (error) {
    console.error("Failed to send feedback:", error);
    return { success: false, message: "Network error or server is down." };
  }
}