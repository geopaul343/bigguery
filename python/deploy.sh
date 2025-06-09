#!/bin/bash

# Exit on any error
set -e

# Configuration
PROJECT_ID="app-audio-analyzer"  # Your GCP project ID
REGION="us-central1"            # Default region (you can change if needed)
SERVICE_NAME="data-api"         # Name of your Cloud Run service
DB_INSTANCE="my-app-database"   # Your Cloud SQL instance name

# Set environment variables for database connection
export INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:$DB_INSTANCE"
export DB_USER="postgres"
export DB_NAME="postgres"  # Default database name, change if you created a different one

# Build and push the container
echo "Building and pushing container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="INSTANCE_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME" \
  --set-env-vars="DB_USER=$DB_USER" \
  --set-env-vars="DB_NAME=$DB_NAME" \
  --set-secrets="DB_PASS=db-password:latest" \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME

# Get the service URL
echo "Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')
echo "Your service is deployed at: $SERVICE_URL"
echo ""
echo "You can use this endpoint to store data by sending POST requests to: $SERVICE_URL/store-data"
echo "Example curl command:"
echo "curl -X POST $SERVICE_URL/store-data \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"your_data\": \"your_value\"}'" 