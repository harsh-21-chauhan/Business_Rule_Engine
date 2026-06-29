# Dynamic Business Rules Engine (BRE)

A powerful, dynamic Business Rules Engine built with Django. It allows modern enterprises (like banks, insurance, and healthcare organizations) to configure and evaluate complex decision logic (e.g., loan approvals, fraud detection) entirely through a web interface, without needing to hardcode if/else statements in the backend.

## 🌟 Key Features

- **Database-Driven Logic:** All business rules are stored in a SQLite database and evaluated dynamically at runtime. No hardcoded logic.
- **Rule Categories:** Supports Mandatory (stop on fail), Scoring (adds weight), Warning, and Informational rules.
- **Priority Execution:** Rules execute in a defined priority order.
- **Enterprise Approval Workflow:** 
  - The entire platform is secured behind employee authentication.
  - Employees can draft new rules or edit existing ones.
  - Drafts enter a "Pending Approval" state and do not affect live evaluations.
  - Admins (superusers) review, approve, or reject rule drafts.
- **Evaluation & Simulation:** Built-in forms to test rules against sample application data, both securely saved (Evaluation) and sandbox (Simulation).
- **History & Auditing:** Full logs of every evaluation, including who ran it, the final score, rules passed/failed, and a detailed human-readable explanation.

## 🛠️ Tech Stack

- **Backend:** Python, Django 5
- **Database:** SQLite (built-in)
- **Frontend:** HTML5, pure CSS (Custom Dark Theme)
- **Architecture:** Standard Django MVT (Model-View-Template) with no REST APIs or external JS frameworks for maximum simplicity and maintainability.

## ⚙️ Core Technical Design

### The Evaluator Engine
The heart of the application is `Rules/evaluator.py`. When an application is submitted, the engine:
1. Fetches all rules where `is_active=True` and `status='active'`.
2. Sorts them by `priority`.
3. Processes Mandatory rules first (rejecting immediately if any fail).
4. Processes Scoring rules, summing their `weight` to calculate a `final_score`.
5. Compares the `final_score` against the active `DecisionThreshold` (e.g., >= 80 Approved, >= 60 Manual Review).
6. Generates a JSON-serializable log and a human-readable explanation.

### Approval Workflow
- `BusinessRule` model includes a `status` field (`active`, `pending`, `rejected`) and a self-referential `parent_rule` ForeignKey.
- When a normal employee edits an active rule, a new draft instance is created (`status='pending'`) linked to the original.
- The Evaluator Engine strictly filters by `status='active'`, meaning pending drafts are ignored until an Admin approves them and merges the changes.

## 🚀 Setup Instructions

### 1. Clone the repository and navigate to the project directory
```bash
cd Business_Rule_Engine/BRE
```

### 2. Create and run migrations
```bash
python3 manage.py makemigrations
python3 manage.py migrate
```

### 3. Load Sample Data (Optional but recommended)
Loads 11 pre-configured rules (fraud checks, credit score scoring, etc.) for a loan approval demo.
```bash
python3 manage.py load_sample_rules
```

### 4. Create an Admin Account
You need a superuser account to approve rule changes and access the Django admin panel.
```bash
python3 manage.py createsuperuser
```

### 5. Run the Server
```bash
python3 manage.py runserver
```

Navigate to `http://127.0.0.1:8000/` in your browser. Log in with your new admin account to access the dashboard and rule configurations.