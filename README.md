# Fresh Stock: a small Oracle PL/SQL mini-project

This version keeps the project simple: add food stock, see expiry status, scan for expiry alerts, and record actual food waste. Oracle PL/SQL handles expiry and waste rules. Flask connects the web page to Oracle.

## What stays in the project

- `00_create_user.sql` — makes the Oracle `FOOD_ADMIN` account.
- `database/setup.sql` — creates the small schema, sample records, and PL/SQL program units.
- `backend/` — Flask application and Oracle connection pool.
- `frontend/` — one HTML page, stylesheet, and browser script.
- `.env.example` — example database configuration; the real `.env` is not committed.

## Step 1: Create the Oracle user

In VS Code install/open the Oracle SQL Developer extension. Connect to your Oracle **PDB** (for example `FREEPDB1`) with an administrator account. Open `00_create_user.sql`, choose **Run Script**, and enter a strong password when prompted.

Create a second Oracle connection named `FOOD_ADMIN` with the same PDB service and the password you entered. Run all later database scripts using this connection.

If the extension cannot handle the password prompt, run the statements in a SQL worksheet and type your chosen password there. Do not save it in the project.

## Step 2: Create and seed the mini-project schema

Open `database/setup.sql`, select the `FOOD_ADMIN` connection, and choose **Run Script** (often F5). This creates the tables and procedures and inserts three sample food items.

**Warning:** rerunning `database/setup.sql` drops and recreates the mini-project tables, deleting their current data.

## Step 3: Configure Flask

From PowerShell in the project folder:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with the Oracle username, the password you selected, and the PDB DSN. A common DSN format is `localhost:1521/FREEPDB1`. Then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python backend\app.py
```

Open `http://127.0.0.1:5000`. The app shows inventory and alerts, lets you add products, and lets you record actual waste. Waste recording and stock reduction happen in the same Oracle transaction.

Check the API connection in another PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

## Common errors

- `ORA-65096`: connect to your pluggable database, not `CDB$ROOT`.
- `ORA-00942`: confirm you ran `database/setup.sql` as `FOOD_ADMIN`.
- Missing environment variables: ensure `.env` is in the project root and contains `ORACLE_USER`, `ORACLE_PASSWORD`, and `ORACLE_DSN`.
- Oracle connection failure: check that Oracle/listener is running and that the DSN service name is correct.

The sample user list is a classroom demo, not production authentication. Replace demo setup and add secure login before deploying this application.
