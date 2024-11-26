Just a little home project to scan Tesla API for cars in used inventory and keep up-to-date PostgreSQL database with price changes, mileage, colors, trims etc.

Sends alerts on new cars and price changes, used a Telegram bot for this one.

To use for your area code you'll have to change ZIP and Country code in `html_url`, ideally just open Tesla inventory and look up the URL it's using to fetch data, then update it in `api_urls`.

The database should be initialized with `db/init.sql`.
