# GitCompass Manual

This manual provides instructions on how to set up, run, and test the GitCompass application manually.

## 🛠️ Setup & Configuration

### Prerequisites
- **Node.js** (v18 or higher, recommended v22 LTS)
- **Python** (v3.11 or higher)
- **Supabase Account** with an active project

### 1. Database Configuration
1. Go to your Supabase Dashboard and navigate to the **SQL Editor**.
2. Copy the contents of `backend/supabase/migrations/001_initial_schema.sql` and `backend/supabase/migrations/002_analytics_rpc.sql` and run them. This will create the necessary tables (`profiles`, `repositories`, `commits`, `file_diffs`), RLS policies, triggers, and the analytics RPC function.
3. In the Supabase Dashboard, go to **Authentication -> Providers** and enable **GitHub**. You will need to set up an OAuth app in GitHub Developer Settings and provide the Client ID and Client Secret here.
4. Go to **Authentication -> URL Configuration** and add `http://localhost:5173` to the Redirect URLs.

### 2. Environment Variables
You need to configure environment variables for both the backend and frontend.

**Backend (`backend/.env`):**
Copy `backend/.env.example` to `backend/.env` and fill in the values from your Supabase project settings (API Settings):
```ini
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
SUPABASE_JWT_SECRET="your-jwt-secret"
```

**Frontend (`frontend/.env`):**
Copy `frontend/.env.example` to `frontend/.env` and fill in the values:
```ini
VITE_SUPABASE_URL="https://your-project-id.supabase.co"
VITE_SUPABASE_ANON_KEY="your-anon-key"
```

---

## 🚀 Running the Application

You need to run both the backend FastAPI server and the frontend Vite development server.

### Start the Backend
Open a terminal and run the following commands:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The backend API will be available at `http://localhost:8000`. You can view the interactive API documentation at `http://localhost:8000/docs`.

### Start the Frontend
Open a new terminal and run the following commands:
```bash
cd frontend
npm install
npm run dev
```
The frontend application will be available at `http://localhost:5173`. The Vite server is configured to proxy API requests starting with `/api` to the backend server.

---

## 🧪 Testing

### Backend Automated Tests
The backend includes unit and integration tests using the standard Python `unittest` framework. To run the tests:
```bash
cd backend
source .venv/bin/activate
python -m unittest discover tests
```
This will run tests for the extractor logic (`test_extractor.py`) and API endpoints (`test_api_repositories.py`).

### Frontend Build Test
To ensure the frontend code compiles correctly without errors:
```bash
cd frontend
npm run build
```

---

## 🖱️ Manual End-to-End Testing (UI)

1. **Login:** Open `http://localhost:5173` in your browser. You should see the login page. Click "Continue with GitHub" to authenticate.
2. **Dashboard:** Once authenticated, you will be redirected to the Dashboard. Verify that the "API Status" badge in the top right shows "Connected" (green), indicating successful communication with the backend health endpoint.
3. **Add Repository:**
   - Click the "Add Repository" button.
   - Enter a valid public GitHub repository URL (e.g., `https://github.com/octocat/Hello-World`).
   - Click "Mine Repository".
4. **Mining Process:**
   - The new repository will appear in the list with a "Pending" or "Cloning…" status.
   - The dashboard automatically polls the backend every 3 seconds.
   - You should see the status transition from `Pending` -> `Cloning…` -> `Mining Git log…` -> `Ready`.
   - Once `Ready`, the total number of commits and files extracted will be displayed.
5. **Delete Repository:**
   - Click the trash can icon next to a repository to delete it.
   - This will remove the repository and cascade delete all associated commits and file diffs from the database.
