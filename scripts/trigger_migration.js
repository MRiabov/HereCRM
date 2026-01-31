/**
 * Railway Function: Trigger Database Migration
 * 
 * This script triggers the Alembic migration endpoint for HereCRM.
 * Configuration:
 * - API_URL: The base URL of your FastAPI backend (e.g., https://api-prod.railway.app)
 * - ADMIN_SECRET: The secret key configured in your backend environment variables.
 */

async function triggerMigration() {
    const apiUrl = process.env.API_URL;
    const adminSecret = process.env.ADMIN_SECRET || process.env.CRON_SECRET;

    if (!apiUrl) {
        console.error("Error: API_URL environment variable is not set.");
        process.exit(1);
    }

    if (!adminSecret) {
        console.error("Error: ADMIN_SECRET (or CRON_SECRET) environment variable is not set.");
        process.exit(1);
    }

    const endpoint = `${apiUrl}/api/v1/pwa/maintenance/migrate`;
    
    console.log(`Triggering migration at: ${endpoint}`);

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'X-Admin-Secret': adminSecret,
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (response.ok) {
            console.log("Success:", data.message);
        } else {
            console.error(`Error (${response.status}):`, data.detail || response.statusText);
            process.exit(1);
        }
    } catch (error) {
        console.error("Fetch failed:", error.message);
        process.exit(1);
    }
}

triggerMigration();
