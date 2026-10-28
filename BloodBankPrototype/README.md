# BloodLink — Blood Bank Distribution & Hospital Matching Prototype

A beginner-friendly academic prototype built with **HTML, CSS, JavaScript, Python Flask and SQLite**.

## Features
- Blood group inventory with low-stock indicators
- Create hospital requests with Critical / High / Normal urgency
- Allocation action that checks available units for the exact requested blood group
- Shortest delivery route using Dijkstra's algorithm on a sample weighted graph
- SQLite persistence
- Reset demo data button
- Dashboard counters and responsive layout

## Run on Windows (VS Code)

1. Install Python 3.10 or newer and VS Code.
2. Extract this ZIP and open the `BloodBankPrototype` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

5. Activate it in PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run:

   ```bat
   .venv\Scripts\activate.bat
   ```

6. Install Flask:

   ```powershell
   pip install -r requirements.txt
   ```

7. Start the website:

   ```powershell
   python app.py
   ```

8. Open the local address shown in the terminal, usually `http://127.0.0.1:5000`.

## Quick demo flow
1. Review the starting blood inventory.
2. Add a request, for example City Hospital, O+, 2 units, Critical.
3. Click **Allocate + route** in the request table.
4. Observe stock decrease, request status change to Allocated, and the Dijkstra route.
5. Try requesting more units than available to demonstrate stock validation.
6. Use **Reset demo** to restore the original sample data.

## DAA concepts to explain
- **Dijkstra:** shortest path in a weighted graph; priority queue implementation is approximately O((V + E) log V).
- **Greedy priority idea:** the request table displays Critical, then High, then Normal requests first. The current allocation action is user-triggered; it does not automatically process all requests.
- **Database lookup:** stock is queried by blood group and updated transactionally in SQLite.

## Important limitations
This is a college demonstration using fictional stock and illustrative road distances. It is **not suitable for real clinical use**. The allocation checks only the exact requested group as a simplified rule; real transfusion compatibility depends on patient details, component type, crossmatching, testing, expiry, and qualified blood-bank staff. Do not use this prototype to make medical decisions.
