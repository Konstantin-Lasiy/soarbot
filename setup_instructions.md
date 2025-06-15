# SoarBot Setup Instructions

This guide will help you set up the complete SoarBot system with Supabase, FastAPI backend, React frontend, and GitHub Actions.

## Prerequisites

- Supabase account
- Telegram Bot Token
- GitHub repository with Actions enabled
- Node.js 18+ and Python 3.9+
- uv (Python package manager)

## 1. Supabase Setup

### Create a new Supabase project
1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your Project URL and anon key from Settings > API

### Set up the database
1. Go to the SQL Editor in your Supabase dashboard
2. Run the SQL commands from `database_schema.sql`
3. This will create the necessary tables and security policies

### Configure Authentication
1. In Supabase Dashboard, go to Authentication > Settings
2. Configure your desired authentication providers
3. Add your frontend URL to the allowed redirect URLs

## 2. Backend Setup

### Environment Variables
1. Copy `backend/.env.example` to `backend/.env`
2. Fill in your Supabase credentials:
```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Install Dependencies and Run
```bash
cd backend
uv sync
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## 3. Frontend Setup

### Environment Variables
1. Copy `frontend/.env.example` to `frontend/.env`
2. Fill in your configuration:
```
REACT_APP_SUPABASE_URL=https://your-project-id.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-anon-key
REACT_APP_API_URL=http://localhost:8000
```

### Install Dependencies and Run
```bash
cd frontend
npm install
npm start
```

The frontend will be available at `http://localhost:3000`

## 4. GitHub Actions Setup

### Repository Secrets
Add the following secrets to your GitHub repository (Settings > Secrets and variables > Actions):

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key (not the anon key!)
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `ADMIN_TELEGRAM_CHAT_ID`: Your Telegram chat ID for error notifications
- `SYNOPTIC_API_TOKEN`: Your Synoptic API token

### Workflow Configuration
The workflow in `.github/workflows/soarbot-notifications.yml` will:
- Run every 15 minutes during daylight hours
- Check weather conditions for all active users
- Send personalized notifications based on user preferences
- Log all notifications to the database

## 5. Telegram Bot Setup

### Create a Telegram Bot
1. Message @BotFather on Telegram
2. Use `/newbot` command and follow instructions
3. Save the bot token for your environment variables

### Get Your Chat ID
1. Start a conversation with your bot
2. Send a message to your bot
3. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find your chat ID in the response

## 6. User Registration Flow

### Option 1: Direct Database Entry
For initial testing, you can manually add users to the database:

```sql
-- Insert a user
INSERT INTO users (telegram_chat_id, username, first_name) 
VALUES ('YOUR_CHAT_ID', 'your_username', 'Your Name');

-- The user_configurations table will be automatically populated with defaults
```

### Option 2: Frontend Registration
1. Users create an account through the React frontend
2. They fill in their Telegram chat ID in their profile
3. Configure their notification preferences
4. The system will automatically create the necessary database entries

## 7. Testing

### Test the Backend
```bash
cd backend
uv run python -m pytest  # If you add tests
```

### Test the Lambda Function Locally
```bash
# Make sure you have a .env file with all required variables
python lambda_function.py
```

### Test GitHub Actions
1. Push your changes to GitHub
2. Go to Actions tab in your repository
3. Manually trigger the workflow or wait for the scheduled run
4. Check the logs to ensure everything works

## 8. Deployment

### Backend Deployment
Deploy the FastAPI backend to your preferred platform:
- Heroku
- Railway
- AWS Lambda (with Mangum)
- Google Cloud Run
- DigitalOcean App Platform

### Frontend Deployment
Deploy the React frontend to:
- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages

Update the CORS settings in your backend and the API URL in your frontend accordingly.

## 9. Monitoring

### Database Monitoring
- Monitor the `notification_history` table for sent notifications
- Check `users` table for active users
- Review `user_configurations` for preference changes

### GitHub Actions Monitoring
- Check the Actions tab for workflow runs
- Set up notifications for failed runs
- Monitor the logs for any errors

### Telegram Bot Monitoring
- Test the bot regularly
- Monitor error messages sent to admin chat
- Check message delivery rates

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Verify Supabase URL and keys
   - Check network connectivity
   - Ensure RLS policies are correctly configured

2. **Telegram Bot Not Working**
   - Verify bot token is correct
   - Check chat IDs are valid
   - Ensure users have started the bot

3. **GitHub Actions Failing**
   - Check all secrets are correctly set
   - Verify Python dependencies
   - Review workflow logs for specific errors

4. **Frontend Authentication Issues**
   - Verify Supabase configuration
   - Check redirect URLs
   - Ensure CORS is properly configured

### Getting Help

- Check the GitHub repository issues
- Review Supabase documentation
- Consult FastAPI and React documentation
- Check Telegram Bot API documentation