# Make.com Integration Guide

This guide provides step-by-step instructions for integrating the Forex Bot API with Make.com for automated scheduling.

## Overview

The integration consists of two main automated workflows:
1. **Data Loading** (05:00) - Updates forex data including actual impact values
2. **Today News Distribution** (07:00) - Sends today's news to all active users

## Prerequisites

- Active Make.com account
- Deployed API server accessible via public URL
- API server running and responding to health checks

## API Endpoints

Your API server provides these endpoints for automation:

- **Health Check**: `GET /health`
- **Load Data**: `POST /api/load-data`
- **Send Today**: `POST /api/send-today`
- **Status**: `GET /api/status`

Replace `YOUR_API_URL` with your actual API server URL (e.g., `https://your-app.onrender.com`).

## Scenario 1: Data Loading (05:00 Daily)

### Step 1: Create New Scenario
1. Log into Make.com
2. Click **"Create a new scenario"**
3. Name it "Forex Data Loading - 05:00"

### Step 2: Add Schedule Trigger
1. Click the **"+"** button to add a module
2. Search for **"Schedule"** and select it
3. Choose **"Every day"**
4. Set time to **05:00** (your timezone)
5. Click **"OK"**

### Step 3: Add HTTP Request Module
1. Click the **"+"** button after the schedule
2. Search for **"HTTP"** and select **"Make a request"**
3. Configure the HTTP module:
   - **URL**: `YOUR_API_URL/api/load-data`
   - **Method**: `POST`
   - **Headers**: 
     ```
     Content-Type: application/json
     ```
   - **Body type**: `Raw`
   - **Content type**: `JSON (application/json)`
   - **Request content**:
     ```json
     {
       "days_ahead": 5
     }
     ```

### Step 4: Add Error Handling (Optional)
1. Right-click on the HTTP module
2. Select **"Add error handler"**
3. Add notification modules (email, Slack, etc.) to alert on failures

### Step 5: Test and Activate
1. Click **"Run once"** to test
2. Verify the API responds successfully
3. Click **"Scheduling"** toggle to activate

## Scenario 2: Today News Distribution (07:00 Daily)

### Step 1: Create New Scenario
1. Create another new scenario
2. Name it "Forex Today News - 07:00"

### Step 2: Add Schedule Trigger
1. Add **"Schedule"** module
2. Choose **"Every day"**
3. Set time to **07:00** (your timezone)

### Step 3: Add HTTP Request Module
1. Add **"HTTP"** > **"Make a request"** module
2. Configure:
   - **URL**: `YOUR_API_URL/api/send-today`
   - **Method**: `POST`
   - **Headers**: 
     ```
     Content-Type: application/json
     ```
   - **Body type**: `Raw`
   - **Content type**: `JSON (application/json)`
   - **Request content**: `{}` (empty JSON object)

### Step 4: Add Success Logging (Optional)
1. Add another HTTP module after the first one
2. Configure it to log success to your monitoring system
3. Use a filter to only run on successful responses

### Step 5: Test and Activate
1. Test the scenario
2. Activate scheduling

## Advanced Configuration

### Health Monitoring Scenario

Create a third scenario for health monitoring:

1. **Schedule**: Every 15 minutes
2. **HTTP Request**: `GET YOUR_API_URL/health`
3. **Filter**: Only proceed if status is not "healthy"
4. **Notification**: Send alert via email/Slack

### Error Handling Best Practices

1. **Retry Logic**: Configure HTTP modules to retry failed requests
2. **Timeout Settings**: Set appropriate timeouts (30-60 seconds)
3. **Status Code Handling**: Handle different HTTP status codes appropriately
4. **Logging**: Log all requests and responses for debugging

### Example Error Handler Configuration

```json
{
  "retry": {
    "max_attempts": 3,
    "interval": 60,
    "exponential_backoff": true
  },
  "timeout": 60,
  "expected_status_codes": [200, 201]
}
```

## Monitoring and Troubleshooting

### Checking Scenario Execution
1. Go to **"Scenarios"** in Make.com
2. Click on your scenario
3. View **"Execution history"** tab
4. Check for errors or failed executions

### Common Issues

1. **API Server Not Responding**
   - Check if your API server is running
   - Verify the URL is correct and accessible
   - Check firewall settings

2. **Authentication Errors**
   - Ensure no authentication is required for the endpoints
   - If authentication is needed, add appropriate headers

3. **Timeout Errors**
   - Increase timeout settings in HTTP modules
   - Check if API operations are taking too long

4. **Schedule Not Running**
   - Verify scenario is activated
   - Check timezone settings
   - Ensure Make.com account has sufficient operations

### Testing API Endpoints Manually

Use curl to test endpoints before setting up Make.com:

```bash
# Health check
curl -X GET "YOUR_API_URL/health"

# Load data
curl -X POST "YOUR_API_URL/api/load-data" \
  -H "Content-Type: application/json" \
  -d '{"days_ahead": 5}'

# Send today
curl -X POST "YOUR_API_URL/api/send-today" \
  -H "Content-Type: application/json" \
  -d '{}'

# Status check
curl -X GET "YOUR_API_URL/api/status"
```

## Expected API Responses

### Successful Data Loading Response
```json
{
  "success": true,
  "result": {
    "status": "success",
    "events_loaded": 25,
    "errors_count": 0,
    "duration_seconds": 45,
    "start_date": "2025-06-23",
    "end_date": "2025-06-28"
  },
  "timestamp": "2025-06-24T05:00:00"
}
```

### Successful Today News Response
```json
{
  "success": true,
  "result": {
    "status": "success",
    "users_notified": 15,
    "errors_count": 0,
    "total_users": 15
  },
  "timestamp": "2025-06-24T07:00:00"
}
```

## Security Considerations

1. **API Security**: Consider adding API key authentication if needed
2. **Rate Limiting**: Make.com respects rate limits automatically
3. **HTTPS**: Always use HTTPS for API endpoints
4. **Monitoring**: Monitor API access logs for unusual activity

## Support and Maintenance

1. **Regular Testing**: Test scenarios monthly to ensure they work
2. **API Updates**: Update Make.com scenarios when API changes
3. **Backup Scenarios**: Export scenario configurations as backups
4. **Documentation**: Keep this guide updated with any changes

## Conclusion

This integration automates the forex bot's data loading and news distribution, eliminating the need for manual intervention. The scheduled workflows ensure users receive timely updates while maintaining data accuracy through regular updates.

For additional support, refer to:
- [Make.com Help Center](https://help.make.com/)
- [Make.com Community](https://community.make.com/)
- Your API server logs and monitoring
