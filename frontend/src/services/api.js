const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function readJsonResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data?.detail || data?.message || "Request failed";
    throw new Error(message);
  }
  return data;
}

export const getArticles = async (filters = {}) => {
  const params = new URLSearchParams(filters);
  const response = await fetch(`${BASE_URL}/articles?${params.toString()}`);
  return readJsonResponse(response);
};

export const getBriefings = async (language = "en") => {
  const response = await fetch(`${BASE_URL}/briefings/today?language=${language}`);
  return readJsonResponse(response);
};

export const getPipelineStatus = async () => {
  const response = await fetch(`${BASE_URL}/status`);
  return readJsonResponse(response);
};

export const askNewsroomQuestion = async ({ question, history = [], language = "en", limit = 5, hoursBack = 2160 }) => {
  const response = await fetch(`${BASE_URL}/qa`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      language,
      limit,
      hours_back: hoursBack,
      messages: history,
    }),
  });

  return readJsonResponse(response);
};
