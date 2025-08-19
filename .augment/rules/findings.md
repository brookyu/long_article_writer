# Findings and Solutions

This file documents problems encountered and their solutions for future reference.

## Database Connection Issues

### Problem
- MySQL connection errors when using default port 3306
- Database not accessible from application

### Solution
- MySQL is running on port 3307, not the default 3306
- Update connection strings to use: `mysql -h 127.0.0.1 -P 3307 -u root -D long_article_writer`
- Backend configuration already correctly uses port 3307

### Prevention
- Always check actual running ports with `docker-compose ps`
- Verify database connectivity before assuming connection issues are code-related

## Knowledge Base Search Functionality Issues

### Problem
- Frontend search always returned "No documents match your search"
- Backend API was working correctly but frontend couldn't display results

### Root Causes & Solutions

#### 1. API Response Format Mismatch
**Problem**: Frontend expected `matches` array but backend returned `results` array
**Solution**: Updated frontend to use `response.results` instead of `response.matches`

#### 2. Field Name Mismatches
**Problem**: Frontend expected different field names than backend provided
- Frontend: `relevance_score` → Backend: `score`
- Frontend: `preview` → Backend: `text`
- Frontend: `filename` → Backend: not provided directly

**Solution**: 
- Updated frontend interface to match backend response format
- Added document name fetching to display actual filenames
- Updated UI components to use correct field names

#### 3. Score Threshold Too High
**Problem**: Score threshold of 0.7 was too restrictive, filtering out relevant results
**Solution**: Lowered threshold to 0.2 for better recall while maintaining relevance

#### 4. Frontend Port Configuration
**Problem**: Frontend running on wrong port (3006) without proper proxy setup
**Solution**: 
- Ensured frontend runs on port 3005 as configured in vite.config.ts
- Verified proxy configuration routes `/api` calls to `http://localhost:8001`
- Killed conflicting processes on port 3005

#### 5. Collection Data Issues
**Problem**: Some collections had documents pointing to deleted temporary files
**Solution**: 
- Identified Collection 3 as fully functional with 30 indexed entities
- Collection 7 needs document re-upload due to missing temporary files
- Collection 2 has partial indexing (16/41 chunks)

### Verification Tests
- Chinese queries: "工作流程" (5+ results), "海关" (1+ results)
- English queries: "food safety inspection" (3+ results), "customs inspection" (3+ results)
- Response times: <1 second
- Relevance scores: 20-70% range with meaningful semantic matching

### Prevention
- Always verify API response format matches frontend expectations
- Test with actual data before assuming search algorithms are broken
- Check network connectivity and proxy configuration first
- Use proper port configurations as defined in config files
- Implement comprehensive logging for debugging data flow issues
