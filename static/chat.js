// chat.js — محادثة بسام الذكي (واجهة المستخدم + بث حي)

const chatBox = document.getElementById("chat-box");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

// إضافة رسالة في واجهة المحادثة
function appendMessage(sender, text) {
  const msg = document.createElement("div");
  msg.className = sender === "user" ? "msg user" : "msg bot";
  msg.innerHTML = `<b>${sender === "user" ? "🧑‍💻 أنت" : "🤖 بسّام"}:</b> ${text}`;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// إرسال السؤال وتشغيل البث الحي (SSE)
async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;
  appendMessage("user", text);
  input.value = "";

  const eventSource = new EventSource(`/ask_stream?q=${encodeURIComponent(text)}`);

  let fullResponse = "";

  eventSource.onmessage = (event) => {
    const chunk = event.data;
    if (chunk === "[DONE]") {
      eventSource.close();
      return;
    }
    fullResponse += chunk + " ";
    // تحديث الرسالة الأخيرة في الوقت الحقيقي
    updateLastBotMessage(fullResponse);
  };

  eventSource.onerror = () => {
    eventSource.close();
    appendMessage("bot", "⚠️ حدث خطأ أثناء استقبال الرد.");
  };

  // إنشاء مبدئي لرسالة البوت
  appendMessage("bot", "...");
}

// تحديث آخر رسالة بوت أثناء الكتابة
function updateLastBotMessage(text) {
  const botMessages = document.querySelectorAll(".msg.bot");
  const last = botMessages[botMessages.length - 1];
  if (last) last.innerHTML = `<b>🤖 بسّام:</b> ${text}`;
}

// إرسال عند الضغط على الزر أو زر Enter
sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});
