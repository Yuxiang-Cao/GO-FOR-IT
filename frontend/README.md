# 🎨 Vite React Frontend — GO FOR IT UI

The frontend of the system is a modern Single Page Application (SPA) built using **React** and **Vite**, styled with custom **Vanilla CSS** for maximum flexibility, aesthetic performance, and design consistency.

---

## 📁 Project Structure

All frontend-related code resides in the `/frontend` directory:
*   [App.jsx](file:///c:/Users/a518028/OneDrive%20-%20Volvo%20Group/repos/learner/frontend/src/App.jsx): Main application container. Manages tab routing, modal dialog overlays, target wizards, CRUD forms, and all state interactions with the FastAPI backend.
*   [index.css](file:///c:/Users/a518028/OneDrive%20-%20Volvo%20Group/repos/learner/frontend/src/index.css): Core design system style definitions. Establishes HSL color tokens, typography classes, layout grids, components, and hover/micro-animations.
*   [main.jsx](file:///c:/Users/a518028/OneDrive%20-%20Volvo%20Group/repos/learner/frontend/src/main.jsx): React application entry point.

---

## 🎨 Nordic Dark Minimalist Design System

Styling uses HSL variables located at the `:root` level of `index.css`. This provides a premium, cohesive Nordic Dark Theme:
*   **Colors**:
    *   `--bg-primary`: Dark slate black (`hsl(220, 15%, 8%)`) for layout backgrounds.
    *   `--bg-secondary`: Charcoal slate (`hsl(220, 12%, 12%)`) for cards and panels.
    *   `--text-primary`: Sleek soft white (`hsl(0, 0%, 93%)`).
    *   `--accent-blue`: Frost blue (`hsl(200, 80%, 60%)`) for primary interactive actions and indicators.
    *   `--accent-green`: Forest green (`#2ea44f`) for success status indicators.
    *   `--accent-red`: Aurora crimson (`#cf222e`) for warnings and deletions.
*   **Typography**: Implements custom font family rules using browser system defaults or imported fonts. Focuses on typographic hierarchy (titles, labels, secondary statuses) to present maximum information readability.
*   **Layout Grid**: Renders a fixed navigation sidebar on the left and a scrollable content area on the right. Form layout sections use flexible CSS grids (`grid-template-columns`).
*   **Interactive Components**: Includes custom CSS animations for modal fade-ins (`modal-overlay`), button hover scales, and clean status tag color-codings.

---

## 🛠️ How to Develop Locally

The FastAPI backend automatically serves the pre-compiled production assets in `frontend/dist/` when you run `python run.py`. 

However, during active frontend development, you can run a dedicated Vite Dev Server with Hot Module Replacement (HMR):

1.  Navigate into the frontend folder:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Launch the Vite developer server:
    ```bash
    npm run dev
    ```
4.  Open `http://localhost:5173` in your browser.
    *   *Note*: The frontend is pre-configured in `App.jsx` to automatically detect port `5173` and proxy backend requests to the FastAPI server at `http://127.0.0.1:8000`. Ensure your backend server is running concurrently.

---

## 📦 Building for Production

When building the final bundle for release:
```bash
npm run build
```
This compiles assets into the `frontend/dist/` directory, which is subsequently packaged and served by FastAPI. Version changes are automated using the main repository helper CLI:
```bash
python scripts/git_helper.py bump patch
```
