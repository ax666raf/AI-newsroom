/*const BASE_URL = "http://localhost:8000/api";

export const getArticles = async (filters = {}) => {
  const params = new URLSearchParams(filters);
  const res = await fetch(`${BASE_URL}/articles?${params}`);
  return res.json();
};

export const getBriefings = async () => {
  const res = await fetch(`${BASE_URL}/briefings`);
  return res.json();
};

export const getPipelineStatus = async () => {
  const res = await fetch(`${BASE_URL}/status`);
  return res.json();
};
```

### `.gitignore`
```
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/
.env

# Database
*.db
*.sql

# Node
node_modules/
dist/
.env.local

# Logs
*.log

# OS
.DS_Store
Thumbs.db*/