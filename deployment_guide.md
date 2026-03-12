# Deployment Guide for CareerFlow (Bring Your Own Key)

To easily deploy this application so others can use it, we recommend using [Streamlit Community Cloud](https://share.streamlit.io/). It is free, optimized for Streamlit applications, and connects directly to your GitHub repository.

## Prerequisites
1. **GitHub Account**: You need a GitHub account to host your code.
2. **Requirements file**: Ensure your project directory has a `requirements.txt` file listing all necessary Python packages. Based on your code, it should include at least:
   ```text
   streamlit
   langchain-google-genai
   SpeechRecognition
   edge-tts
   plotly
   fpdf
   python-dotenv
   pypdf
   streamlit-mic-recorder
   ```

## Step-by-Step Deployment on Streamlit Cloud

1. **Push your code to GitHub:**
   - Create a new repository on your GitHub account.
   - Commit and push `Careerflow.py`, `requirements.txt`, and the `assets` folder.
   - **Important:** Do NOT commit your `.env` file if it contains your personal `GEMINI_API_KEY`. The code has been updated so that users can input their own keys directly in the app (BYOK).

2. **Connect to Streamlit Community Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
   - Click on the **"New app"** button.
   - Fill in the deployment form:
     - **Repository**: Select the repository you just created.
     - **Branch**: Typically `main` or `master`.
     - **Main file path**: Enter `Careerflow.py`.

3. **Configure Secrets (Optional):**
   - If you want the app to have a default API built-in (so users don't have to input their own unless they want to), you can set secrets.
   - Click on **"Advanced settings"** before deploying, or go to **Settings > Secrets** from your deployed app dashboard.
   - Add your environment variables in TOML format:
     ```toml
     GEMINI_API_KEY = "your-google-api-key-here"
     CAREERFLOW_BASE_URL = "https://your-app-url.streamlit.app"
     ```

4. **Deploy!**
   - Click **"Deploy!"**
   - Streamlit will launch a server, install the dependencies from your `requirements.txt`, and run `Careerflow.py`.
   - Once it's ready, your app will be live and accessible via a public URL! 

Now, when users visit your app, they will see a text input in the sidebar asking them for their Gemini API Key, allowing them to use their own billing and usage limits while enjoying your application.
