```markdown
# Technical Specification: Setup Supabase Database Tables

## 1. Summary
The objective is to create two Supabase database tables: `personalization_jobs` and `personalization_outputs`, to store personalization job data and their respective outputs. These tables will facilitate storing and retrieving information necessary for personalization processing, including job parameters and outputs in JSON format. 

## 2. Implementation Steps

### Step 1: Define Table Structure
- **Table 1: `personalization_jobs`**
  - Columns: 
    - `id`: Primary Key, auto-incremented integer.
    - `created_at`: Timestamp of when the job was created, defaulting to the current time.
    - `email`: Email address as a string, max length 255.
    - `domain`: Domain related to the job, max length 255.
    - `cta`: Call-to-action as a string, max length 50.
    - `persona`: Persona type as a string, max length 50.
    - `buyer_stage`: Stage in the buying process as a string, max length 50.
    - `company_name`: Name of the company, max length 255.
    - `industry`: Industry sector, max length 100.
    - `company_size`: Size of the company, max length 50.
    - `status`: Current status of the job, max length 50.

- **Table 2: `personalization_outputs`**
  - Columns:
    - `job_id`: Foreign Key referencing `personalization_jobs(id)`.
    - `created_at`: Timestamp of when the output was created, defaulting to the current time.
    - `output_json`: JSON field to store output data.

### Step 2: Write SQL Scripts
- Create SQL scripts to define the tables with the specified columns and relationships.
- Ensure the `job_id` in `personalization_outputs` references the `id` in `personalization_jobs` to maintain referential integrity.

### Step 3: Execute SQL Scripts
- Run the SQL scripts in the Supabase SQL Editor to create the tables.
- Verify the tables are created successfully and are accessible for subsequent data operations.

## 3. Tech Stack
- **Database**: Supabase (PostgreSQL)
- **Language**: SQL
- **Tools**: Supabase SQL Editor

## 4. Edge Cases
- Ensure all string fields are appropriately sized to avoid truncation.
- Handle null entries for optional fields where applicable.
- Validate that foreign key constraints are enforced to prevent orphaned records in `personalization_outputs`.
- Test table creation under different scenarios to ensure robustness.
```
