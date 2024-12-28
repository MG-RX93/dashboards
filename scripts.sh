# Start postgres service
brew services start postgresql

# login to postgres
psql -U $(whoami) -d postgres

