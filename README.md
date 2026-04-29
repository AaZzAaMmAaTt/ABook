# ABook - Telegram Book Library Bot 📚

**ABook** is a Telegram bot that serves as a convenient online library. Users can browse books by genre, read PDFs with a built-in timer, track their reading statistics, and much more. With a powerful admin panel, adding new books is quick and effortless.

---

## ✨ Features

### 👤 User Profile
The bot greets every user and provides a **Profile** section that tracks:
- 📅 **Days in the bot** — how long the user has been using ABook
- 📖 **Books read** — total number of completed books
- ⏱️ **Minutes spent reading** — total reading time

### 📋 Menu & Genres
Pressing the **Menu** button opens a list of genres. Each genre contains books related to it. *(Some genres may have fewer books, as books are stored locally to avoid overload.)*

### 🔍 Search & Request System
- Users can **search** for a specific book.
- If a book is **not found**, the user can send a **request to the admin** for it to be added.
- The admin receives an immediate notification and can easily add the book using a pre-formatted template sent by the bot.

### 📖 Reading Experience
- Once a user finds a book, they can **download the PDF** and start reading.
- A **timer** starts automatically to track reading time.
- After finishing, the user presses **"Книга прочтена"** *(Book Read)* to mark it as complete.

### 🔥 Trending Books
Data from how many times the "Book Read" button is pressed is collected to build a **leaderboard of the most popular books**, so users can discover what's currently trending.

### 📌 Continue Reading & Favorites
- If a user doesn't finish a book and doesn't press "Book Read", the book is saved in the **"Continue Reading"** section — they can always open it from there.
- Every book also has an **"Add to Favorites"** button, helping users save and quickly access their beloved books.

---

## 🛠️ Tech Stack

| Area | Technology |
|------|------------|
| **Bot Framework** | Telegram Bot API (Python) |
| **Language** | Python |
| **Database** | SQLite |
| **Books Format** | PDF (stored locally) |

---

> ⚠️ **Language Note:** The bot interface and all interactions are in **Russian**, as the developer's IT education was conducted in Russian.

---

## 🚀 Getting Started

### 🌐 Live Bot
The bot may not always be online, as it's hosted on a local device. If the bot doesn't respond, please message me on Telegram and I'll restart it as soon as possible.

> 💬 **Contact:** [@nematovich_a](https://t.me/nematovich_a)
> 
> 🔗 **Bot link:** *(Add your bot's Telegram link here, e.g., `[https://t.me/@ABookProjectBot](https://t.me/ABookProjectBot)`)*

---

### 💻 Run Locally (Advanced)

> ⚠️ **Important:** Running the bot locally may **not work fully**, as all book files are stored with local paths from the developer's device. For your convenience, the bot is kept running online.  
> If the bot is unresponsive (offline), please contact me on Telegram: **[@nematovich_a](https://t.me/nematovich_a)** — I will restart it immediately.

If you still want to try running it locally:

#### Prerequisites
- Python 3.8 or higher
- Git
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))

#### Step 1: Clone the Repository
```bash
git clone https://github.com/AaZzAaMmAaTt/ABook.git
cd ABook

Step 2: Set Up Environment
Create a .env file in the project root and add your bot token:
BOT_TOKEN=your_telegram_bot_token_here

Step 3: Run the Bot
python main.py

🤝 Connect & Support
If the bot is not responding or you have any questions, feel free to reach out:
💬 Telegram: @nematovich_a
🐙 GitHub Issues: Open an issue
I'll get the bot back online as soon as possible!
Happy reading with ABook! 📚✨
