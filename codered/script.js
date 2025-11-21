// BACKEND URL
const API_URL = "http://127.0.0.1:8080/safe-check";

async function safeCheck(prompt) {
  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });

  if (!res.ok) {
    throw new Error("Request failed with status " + res.status);
  }
  return await res.json();
}

document.getElementById("checkBtn").addEventListener("click", async () => {
  const prompt = document.getElementById("prompt").value.trim();
  const resultDiv = document.getElementById("result");

  if (!prompt) {
    resultDiv.innerHTML = "<p>Please enter a prompt.</p>";
    return;
  }

  resultDiv.innerHTML = "<p>Checking...</p>";

  try {
    const data = await safeCheck(prompt);
    const flagClass = data.flagged ? "flag-true" : "flag-false";
    const flagText = data.flagged ? "FLAGGED ❌" : "NOT FLAGGED ✅";

    resultDiv.innerHTML = `
      <p class="${flagClass}">Overall: ${flagText}</p>
      <pre>${JSON.stringify(data, null, 2)}</pre>
    `;
  } catch (err) {
    console.error(err);
    resultDiv.innerHTML = "<p>Error: " + err.message + "</p>";
  }
});
