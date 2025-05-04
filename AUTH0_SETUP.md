# Setting up Auth0 Authentication

This guide explains how to set up Auth0 authentication for the Writers LLM Backend API.

## 1. Create an Auth0 Account and API

1. Sign up for an Auth0 account at [auth0.com](https://auth0.com/)
2. Go to the Auth0 Dashboard
3. Create a new API:
   - Go to `Applications > APIs` and click `Create API`
   - Provide a name (e.g., "Writers LLM API")
   - Set an Identifier (e.g., "https://api.writers-llm.com")
   - Choose the signing algorithm (RS256 is recommended)

## 2. Configure Environment Variables

Copy the necessary Auth0 configuration values to your `.env` file:

```
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_AUDIENCE=https://your-api-identifier
```

- `AUTH0_DOMAIN`: Your Auth0 tenant domain (e.g., `your-tenant.us.auth0.com`)
- `AUTH0_API_AUDIENCE`: The API identifier you configured in Auth0

## 3. Install Required Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

## 4. Testing the Authentication

### Getting a Test Token

1. In the Auth0 Dashboard, go to your API settings
2. Scroll down to the "Test" tab
3. Here you can obtain a test token to use with your API

### Making Authenticated Requests

Include the Bearer token in the Authorization header:

```bash
curl -X GET "http://localhost:8000/api/v1/books" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 5. Configuring a Client Application

To use this API with a client application:

1. In Auth0 Dashboard, go to `Applications > Applications`
2. Create a new application or select an existing one
3. Configure the application settings, including allowed callback URLs
4. Use the Auth0 SDKs in your client application to handle authentication

## 6. Permissions and Roles (Optional)

You can configure additional permissions and roles in Auth0:

1. In your API settings, go to the "Permissions" tab
2. Add permissions (e.g., `book:read`, `book:write`)
3. Create roles and assign permissions to them
4. Assign roles to users

The permissions will be included in the access token and can be used for more granular access control in your API.
