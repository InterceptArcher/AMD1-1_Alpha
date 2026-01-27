```markdown
# Environment Variables Configuration for Supabase Integration

This document outlines the required environment variables for integrating Supabase with our Next.js application, along with steps for secure storage and configuration.

## Required Environment Variables

1. **NEXT_PUBLIC_SUPABASE_URL**
   - **Description**: The base URL of your Supabase instance.
   - **Usage**: This is a public URL used by the client-side application to communicate with Supabase.

2. **NEXT_PUBLIC_SUPABASE_ANON_KEY**
   - **Description**: The anonymous public API key for Supabase.
   - **Usage**: This key is used for public client-side requests to Supabase. It's safe to expose on the client-side.

3. **SUPABASE_SERVICE_ROLE**
   - **Description**: The service role key for server-side operations.
   - **Usage**: This key should be kept secure and only used in server-side operations due to its elevated permissions.

## Setup Instructions

### Local Development

1. Create a `.env.local` file in the root of your project:

   ```shell
   touch .env.local
   ```

2. Add the following lines to `.env.local`, replacing placeholders with actual values:

   ```shell
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
   SUPABASE_SERVICE_ROLE=your_service_role_key
   ```

3. Ensure `.env.local` is included in your `.gitignore` to keep it out of version control:

   ```shell
   echo ".env.local" >> .gitignore
   ```

### Production Configuration

- Configure environment variables in your hosting provider’s settings:
  - **Vercel**: Navigate to your project settings, and add the environment variables under the "Environment Variables" section.
  - **AWS**: Use the "Environment Variables" section under your AWS Lambda function configuration or Elastic Beanstalk environment settings.

## Accessing Environment Variables

- **Client-side**: Use `process.env.NEXT_PUBLIC_SUPABASE_URL` and `process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY` to access these variables.
- **Server-side**: Access `process.env.SUPABASE_SERVICE_ROLE` for operations that require service role permissions.

## Documentation and Testing

- Ensure these variables are documented within your project’s `README.md` or a dedicated configuration file.
- Test the application thoroughly to verify connectivity with Supabase and correct error handling if variables are misconfigured or missing.

## Troubleshooting

- **Missing Variables**: Verify that all required variables are set in both development and production environments.
- **Invalid Credentials**: Double-check Supabase credentials to ensure they are correct and have not expired.
- **Error Handling**: Implement error handling for scenarios where Supabase integration might fail due to misconfiguration.

This setup enables the secure and effective integration of Supabase services within our Next.js application.
```