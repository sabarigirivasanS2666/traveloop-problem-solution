# Traveloop Local Web Application

A complete local travel-planning web app created using:

- Frontend: HTML, CSS, JavaScript
- Backend: Python Flask
- Database: SQLite

## Features Included

- Login and signup with password hashing
- Forgot password demo screen
- User dashboard / home screen
- Create trip screen
- My Trips list screen
- Itinerary builder with multi-city stops
- Itinerary list/calendar view toggle
- City search with country filter
- Activity search with cost filters
- Trip budget and cost breakdown chart
- Booking manager for hotels, transport, flights, trains, buses, restaurants and activities
- Packing checklist with add, delete, mark packed and reset
- Public/read-only itinerary sharing link
- Copy public trip option
- User profile/settings page
- Trip notes/journal
- Admin analytics dashboard with user management and charts
- SQLite relational database for users, trips, stops, activities, bookings, checklist and notes

## How to Run Locally

1. Extract the ZIP file.
2. Open the extracted folder in VS Code or terminal.
3. Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

4. Install requirements:

```bash
pip install -r requirements.txt
```

5. Run the app:

```bash
python app.py
```

6. Open this in your browser:

```text
http://127.0.0.1:5000
```

To allow your friend to open it on the same Wi-Fi/hotspot, keep the app running on your laptop and give your friend this format:

```text
http://YOUR-LAPTOP-IP:5000
```

Example:

```text
http://192.168.43.120:5000
```

## Default Admin Login

```text
Email: admin@traveloop.local
Password: admin123
```

## Database

The SQLite database file `traveloop.db` is created automatically when you run the app for the first time.

## Notes

This project is designed for local demonstration/hackathon use. For real production deployment, change the Flask secret key, disable debug mode, add email-based password reset, and use stronger server configuration.
