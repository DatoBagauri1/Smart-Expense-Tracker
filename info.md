# Smart Expense Tracker

## Overview

The Smart Expense Tracker is a Flask-based web application that helps users track expenses, visualize spending patterns, plan savings, and forecast future budgets. The application provides an interactive dashboard with charts for expense analysis, supports CRUD operations for expense management, and allows users to set monthly income and savings goals. Built with Flask, SQLite, and Chart.js, it offers a responsive Bootstrap 5 interface for easy expense tracking and financial planning.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Technology Stack**: Bootstrap 5 + Chart.js
- **UI Framework**: Bootstrap 5 for responsive, mobile-first design
- **Visualization**: Chart.js library for interactive charts (pie, bar, and line charts)
- **Template Engine**: Jinja2 (Flask's default) for server-side rendering
- **Design Pattern**: Server-rendered HTML templates with minimal client-side JavaScript

**Rationale**: Chose server-side rendering over SPA framework to keep the application simple and reduce complexity. Bootstrap 5 provides out-of-the-box responsive components, while Chart.js offers powerful yet lightweight charting capabilities.

### Backend Architecture

**Framework**: Flask (Python micro-framework)
- **Routing**: Function-based views for all CRUD operations and dashboard logic
- **Session Management**: Flask's built-in session with secret key for flash messages
- **Data Processing**: Pandas for data aggregation and export functionality
- **Date Handling**: Python's datetime and dateutil for date calculations and forecasting

**Key Routes**:
- `/` - Dashboard with expense analytics and visualizations
- `/add` - Add new expense form
- `/edit/<expense_id>` - Edit existing expense
- `/delete/<expense_id>` - Delete expense
- `/export` - Export expenses to CSV
- `/set_budget` - Configure monthly income and savings goals

**Rationale**: Flask was chosen for its simplicity and minimal boilerplate. The application uses a monolithic architecture in a single `app.py` file, which is appropriate for the scope and makes deployment straightforward. Function-based views keep the code simple and easy to understand.

### Data Storage

**Database**: SQLite3
- **Schema Design**: Two main tables
  - `expenses`: Stores individual expense records (id, amount, category, date, note)
  - `user_budget`: Stores user financial settings (monthly_income, savings_goal)
- **ORM**: Raw SQL queries via sqlite3 module (no ORM layer)
- **Connection Pattern**: Function-based connection management with row factory for dict-like access

**Rationale**: SQLite was selected for zero-configuration deployment and simplicity. The database auto-initializes on first run. No ORM (like SQLAlchemy) was used to minimize dependencies and keep queries transparent. Row factory provides convenient dict-like access to query results.

### Data Analytics & Forecasting

**Processing Layer**: Pandas + Custom Python Logic
- **Expense Categorization**: Predefined categories (Food, Rent, Travel, Entertainment, Bills, Other)
- **Aggregation**: Group by category and time periods for chart data
- **Forecasting**: Simple moving average calculation for next-month budget prediction
- **Export**: CSV generation using Pandas DataFrame

**Rationale**: Pandas handles data aggregation efficiently and simplifies CSV export. The forecasting uses basic statistical methods appropriate for personal finance tracking without overengineering.

### UI/UX Design Patterns

**Responsive Design**: Mobile-first Bootstrap grid system
- **Color Coding**: Success (green) for income, danger (red) for spending, warning for alerts
- **Flash Messages**: Server-side notifications for user actions (success/error feedback)
- **Navigation**: Persistent navbar with quick access to key features
- **Form Validation**: HTML5 validation with required fields

**Chart Types**:
- **Pie Chart**: Category-wise spending distribution
- **Bar Chart**: Daily/weekly/monthly expense trends
- **Line Chart**: Forecasted spending for next month

## External Dependencies

### Python Packages
- **Flask**: Web framework for routing and templating
- **Pandas**: Data manipulation and CSV export
- **python-dateutil**: Advanced date manipulation for forecasting

### Frontend Libraries (CDN)
- **Bootstrap 5.3.0**: CSS framework for responsive UI components
- **Chart.js 4.4.0**: JavaScript charting library for data visualization

### Database
- **SQLite3**: File-based relational database (no external server required)
- Database file: `database.db` (auto-created in application root)

### Environment Variables
- `SESSION_SECRET`: Flask session secret key (defaults to development key if not set)

### Static Assets
- Custom CSS: `/static/css/style.css` for additional styling
- No external image dependencies
- All icons use Unicode emoji characters

**Note**: The application is designed for single-user deployment with no authentication system. All dependencies are lightweight and suitable for platforms like Replit with minimal configuration requirements.