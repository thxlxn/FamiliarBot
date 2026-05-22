# Telegram Reminder Bot

## Overview
This project is a sophisticated Telegram bot designed for personal task management and automated scheduling. Built with Python, it provides a comprehensive reminder system with support for precise scheduling, timezone awareness, multi-language interfaces, and persistent data storage via PostgreSQL.

---

## Features
* **Task Management**: Create, view, update, postpone, and delete reminders interactively.
* **Dynamic Messaging**: Uses Gemini API to format personalized and context-aware reminder notifications.
* **Languages**: Fully localized interface supporting English, Russian, and Ukrainian.
* **Timezone Synchronization**: Automatically detect timezone via location sharing or select it manually from an inline keyboard.

---

## Technical Features
* **Background Processing**: Utilizes a background scheduler to evaluate tasks and dispatch notifications exactly when due.
* **Robust Logging**: Comprehensive logging system that writes background and application errors to a designated log directory with rotation policies.
* **Internationalization**: Supports multiple languages via `i18n`.
* **Debug Mode**: A secure, admin-only developer environment accessible via password. It allows maintainers to execute raw SQL commands directly from the Telegram chat interface for rapid troubleshooting and database inspection.
---

## Installation and Setup
### Clone the repository
```bash
git clone https://github.com/thxlxn/FamiliarBot.git
cd dating-bot
```

### Install dependencies
It is recommended to use a virtual environment.
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### Database Configuration
Ensure PostgreSQL is running. The bot will automatically initialize the required ```users``` and ```tasks``` tables upon execution if the database exists and credentials are correct.

### Environment Variables
Create a ```.env``` file in the root directory and populate it with the following variables:
| <center>**Name**</center> | <center>**Description**</center>                                                     | <center>**Example**</center>      |
| ------------------------- | ------------------------------------------------------------------------------------ | --------------------------------- |
| TELEGRAM_BOT_KEY        | Bot Token from [@BotFather](https://t.me/BotFather)                                  | 9876543:ASDSFDkjdjdsedmD          |
| GEMINI_KEY              | Gemini Token from [Google AI Studio](https://aistudio.google.com/api-keys)                           | AIzaSyDR8kjjE4S2LWnvziSIlN_GMVj9VNOsvdA                             |
| DB_NAME              | The name of your PostgreSQL                                                   | telebot-postgres                              |
| DB_USERNAME                | The name of DB user                                                                   | postgresadm                                 |
| DB_PASSWORD               | The password of your PostgreSQL                                                       | xymUVhznanvEGygr                                 |
| DB_HOST                    | Usually ```localhost``` for localy hosted DB                                        | localhost              |
| DB_PORT                    | The port of your PostgreSQL                                       | 5432              |
| ADMIN_PASS           | (Optional) The password to activate ```/debug```                                     | 123456789 |

### Running the Bot
Execute the main script to start the bot.
```bash
python main.py
```

---

## Usage and Commands
Interact with the bot via the following commands in Telegram:
* ```/start``` - Initialize the bot and configure your timezone.
* ```/help``` - Display the help menu and command list.
* ```/lang``` or ```/language``` - Switch the interface language.
* ```/newreminder``` - Start the interactive workflow to schedule a new task.
* ```/myreminders``` - List all currently scheduled pending tasks.
* ```/updatereminder``` - Modify the title, notes, or schedule of an existing task.
* ```/removereminder``` - Delete a scheduled task.
* ```/me``` - Display the current user profile information.
* ```/debug``` - Enter developer mode (requires admin password).

---

## Project Structure
```text
.
|-- locales/                 # i18n localization JSON files
|-- log/                     # Application logs (auto-generated)
|-- src/
|   `-- familiarbot/
|       |-- bot.py           # Core Telegram bot logic and handlers
|       |-- config.py        # Environment variable configuration
|       |-- database.py      # PostgreSQL database connection and queries
|       |-- i18n.py          # Translation parsing and string formatting
|       `-- logger.py        # Loguru-based logging implementation
|-- .env                     # Environment variables (not tracked in git)
|-- .gitignore               # Git ignore configuration
|-- LICENSE                  # Project license
|-- main.py                  # Application entry point
|-- pyproject.toml           # Project metadata and dependencies
`-- requirements.txt         # Python dependencies list
```

---

## Localization
Translations are managed via JSON files located in the ```locales/``` directory. To add a new language, create a new ```<iso_code>.json``` file within this directory containing the appropriate key-value pairs matching the project's internal string keys.

---

## License
This project is licensed under the **GNU General Public License v3.0** license. See [LICENSE](./LICENSE) for details.
