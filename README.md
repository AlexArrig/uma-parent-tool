# Uma Parent Tool & Roster Viewer

A Flask-based web application designed to help *Uma Musume* players manage their training rosters, analyze inherited factors and skills (including grandparents and rental parents), and optimize breeding parent combinations either locally or through the Uma.moe API.

---

## Features

* **Roster Management**: Upload and parse your local `data.json` (extracted using tools like [UmaExtractor](https://github.com/xancia/UmaExtractor)).
* **Detailed Card Breakdown**: View individual card stats (SPD, STA, PWR, GUT, WIT), rank scores, factor highlights, and parent trees.
* **Skill & Factor Counting**: Automatically computes **Main White Skills** (from character-specific factors) and **Total White Skills** (aggregating the full inheritance tree including grandparents and rental lineage).
* **Local Parent Pairing Tool**: Discover top local parent combinations from your filtered roster to maximize unique white skills.
* **Uma.moe API Integration**: Search and rank external rental parents directly against your local roster using an optional API key.
* **Responsive Modern UI**: Built with Tailwind CSS and a dark-mode optimized layout for smooth navigation.

---

## Tech Stack

* **Backend**: Python, Flask
* **Frontend**: HTML5, JavaScript, Tailwind CSS (via CDN)
* **Data Format**: JSON

---

## Project Structure

```text
├── app.py              # Main Flask application logic & API endpoints
├── data/               # Local storage directory for uploaded JSON data
├── templates/
│   └── index.html      # HTML interface with Tailwind CSS & JavaScript
└── README.md           # Project documentation
