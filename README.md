# Tracklio

Tracklio is a personal expense tracker web app that helps users manage finances by recording expenses and analyzing spending patterns with secure, user-specific cloud storage, making it accessible anytime, anywhere.

## Features

- **User Registration & Login**: Secure user authentication with personalized dashboards.
- **Expense Tracking**: Add, edit, and delete daily expenses.
- **Monthly Expense Visualization**: Interactive graphs to visualize monthly spending with year selection.
- **AI-Powered Insights**: Advanced budgeting suggestions based on spending habits (planned feature).
- **Cloud-Based Storage**: Expenses are stored securely in the cloud, accessible from any device.

## Technologies Used

- **Frontend**: HTML, Tailwind CSS, JavaScript (Teal & White Theme)
- **Backend**: Flask (Python)
- **Database**: MySQL (hosted on Filess.io for cloud storage)
- **Deployment**: Render (Live at [Tracklio](https://tracklio.onrender.com/))
- **AI Integration**: For advanced budgeting and tracking (planned feature)

## Database Structure

- **Database:** `expense_tracker`
  - **credentials**: Stores usernames and passwords of registered users.
  - **expenses**: Stores user-specific expense data.

## Installation

To set up Tracklio locally, follow these steps:

### Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/omkargarad78/Tracklio.git
   cd Tracklio


2. **Create a virtual environment (optional but recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the application**:
    ```bash
    python app.py
    ```

### Usage

- **Register an account** to create your personal dashboard.
- Add expenses with details like date, amount, and item.
- Visualize monthly expenses using the year filter for trend analysis.
- Manage your data securely, with each user having isolated access.
