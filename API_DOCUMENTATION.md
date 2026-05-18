# API Documentation - Frontend Integration Guide

> Version: 2.0 | Base URL: `http://localhost:8000`

This backend is designed for a Telegram Mini App frontend. Users authenticate with Telegram `initData`, the backend verifies that payload with the Telegram bot token, then returns a JWT for normal API requests.

## Authentication

### Telegram Auth Flow

1. Read `window.Telegram.WebApp.initData` in the Mini App.
2. Send it to `POST /auth/telegram`.
3. Store the returned `access_token`.
4. Use `Authorization: Bearer <token>` for document endpoints.

### POST /auth/telegram

Authenticate a Telegram Mini App user and receive a backend JWT.

**Request**

```http
POST /auth/telegram
Content-Type: application/json

{
  "init_data": "query_id=...&user=%7B...%7D&auth_date=...&hash=..."
}
```

**Response (200 OK)**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "telegram_id": 123456789,
    "username": "microlearn_user",
    "first_name": "Bek",
    "last_name": null,
    "photo_url": null
  }
}
```

**Errors**

| Status | Detail |
|--------|--------|
| 401 | Invalid Telegram signature |
| 401 | Telegram auth data expired |

## Endpoints Overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/telegram` | No | Verify Telegram Mini App user and get JWT |
| POST | `/documents` | Yes | Upload document (async processing) |
| GET | `/documents` | Yes | List current user's documents |
| GET | `/documents/{id}/status` | Yes | Get document processing status |
| GET | `/documents/{id}/lessons` | Yes | Get generated lessons |

## Document Endpoints

### POST /documents

Upload an educational `pdf`, `pptx`, or `docx` file for AI processing.

```http
POST /documents
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary>
```

**Response (202 Accepted)**

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

### GET /documents

Return all documents owned by the authenticated user.

### GET /documents/{doc_id}/status

Return:

```json
{
  "status": "pending"
}
```

### GET /documents/{doc_id}/lessons

Return the generated lesson feed for a completed document.

```json
[
  {"type": "fact", "text": "Mitochondria produce ATP via oxidative phosphorylation."},
  {
    "type": "mcq",
    "question": "What do mitochondria produce?",
    "options": ["ATP", "DNA", "RNA", "Glucose"],
    "answer": "ATP",
    "explanation": "Mitochondria generate ATP through oxidative phosphorylation."
  }
]
```

## Processing Flow

1. Upload a document.
2. Poll `GET /documents/{id}/status` until the status becomes `completed` or `failed`.
3. Fetch lessons with `GET /documents/{id}/lessons`.

## Provider Assumptions

- Database: Neon PostgreSQL
- AI provider: OpenRouter
- File storage: Cloudinary raw uploads
- Identity source: Telegram Mini App `initData`

## Document Endpoints

### POST /documents

Upload an educational document for AI processing.

**Request**

```http
POST /documents
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary>
```

**Headers**

| Header | Value |
|--------|-------|
| Authorization | Bearer `<access_token>` |
| Content-Type | multipart/form-data |

**Form Data**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | binary | Yes | PDF, PPTX, or DOCX file |

**Constraints**
- Max file size: 10 MB
- Max pages: 50
- Max documents per user: 3 (free trial)

**Response (202 Accepted)**

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

**Errors**

| Status | Detail |
|--------|--------|
| 400 | Unsupported file type (must be PDF, PPTX, or DOCX) |
| 400 | File exceeds size limit |
| 400 | Document exceeds page limit |
| 400 | Invalid or corrupted file |
| 400 | Empty file not allowed |
| 401 | Invalid or expired token |
| 403 | Free trial document limit reached (3 documents) |
| 503 | Storage service unavailable |

---

### GET /documents

List all documents uploaded by the authenticated user.

**Request**

```http
GET /documents
Authorization: Bearer <token>
```

**Response (200 OK)**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_type": "pdf",
    "status": "completed",
    "page_count": 25,
    "created_at": "2024-04-12T10:30:00Z"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "file_type": "pptx",
    "status": "processing",
    "page_count": 15,
    "created_at": "2024-04-12T11:00:00Z"
  }
]
```

**Schema**

```typescript
interface DocumentResponse {
  id: string;          // UUID
  file_type: string;   // "pdf" | "pptx" | "docx"
  status: string;      // "pending" | "processing" | "completed" | "failed"
  page_count: number | null;
  created_at: string;  // ISO 8601 datetime
}
```

---

### GET /documents/{doc_id}/status

Check the processing status of a document.

**Request**

```http
GET /documents/550e8400-e29b-41d4-a716-446655440000/status
Authorization: Bearer <token>
```

**Response (200 OK)**

```json
{
  "status": "completed"
}
```

**Status Values**

| Status | Description |
|--------|-------------|
| pending | Document uploaded, waiting to be processed |
| processing | AI is currently generating lessons |
| completed | Lessons ready for retrieval |
| failed | Processing failed (check error) |

**Errors**

| Status | Detail |
|--------|--------|
| 401 | Invalid or expired token |
| 404 | Document not found or not owned by user |

---

### GET /documents/{doc_id}/lessons

Retrieve the generated lessons (facts and MCQs) from a completed document.

**Request**

```http
GET /documents/550e8400-e29b-41d4-a716-446655440000/lessons
Authorization: Bearer <token>
```

**Response (200 OK)**

```json
[
  {
    "type": "fact",
    "text": "Mitochondria produce ATP via oxidative phosphorylation."
  },
  {
    "type": "fact",
    "text": "ATP synthesis requires an electrochemical gradient."
  },
  {
    "type": "fact",
    "text": "The inner mitochondrial membrane is highly folded."
  },
  {
    "type": "mcq",
    "question": "What do mitochondria produce?",
    "options": ["ATP", "DNA", "RNA", "Glucose"],
    "answer": "ATP",
    "explanation": "Mitochondria generate ATP through oxidative phosphorylation in the inner membrane."
  },
  {
    "type": "fact",
    "text": "The citric acid cycle occurs in the mitochondrial matrix."
  }
]
```

**Schema**

```typescript
// Fact item
interface FactItem {
  type: "fact";
  text: string;
}

// MCQ item
interface MCQItem {
  type: "mcq";
  question: string;
  options: string[];  // Exactly 4 options
  answer: string;    // One of the options
  explanation: string;
}

// Lesson item (union)
type LessonItem = FactItem | MCQItem;
```

**Errors**

| Status | Detail |
|--------|----------|
| 401 | Invalid or expired token |
| 404 | Document not found or not owned by user |
| 409 | Document processing not complete |

---

## Async Processing Flow

Documents are processed asynchronously. Here's the recommended flow:

```
1. Upload Document
   POST /documents
   → Returns 202 with document_id and status="pending"

2. Poll Status
   GET /documents/{id}/status
   → Returns {"status": "pending" | "processing" | "completed" | "failed"}
   → Repeat every 2-5 seconds until status="completed" or "failed"

3. Fetch Lessons (when status="completed")
   GET /documents/{id}/lessons
   → Returns array of fact and MCQ items
```

### Recommended Polling Strategy

```javascript
async function waitForCompletion(documentId, token, onProgress) {
  while (true) {
    const response = await fetch(
      `http://localhost:8000/documents/${documentId}/status`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const { status } = await response.json();
    
    onProgress(status);
    
    if (status === "completed") {
      return true;
    }
    if (status === "failed") {
      return false;
    }
    
    await new Promise(r => setTimeout(r, 3000)); // Wait 3 seconds
  }
}
```

---

## Error Codes

### HTTP Status Code Reference

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async processing started) |
| 400 | Bad Request - invalid input |
| 401 | Unauthorized - invalid or missing token |
| 403 | Forbidden - quota exceeded |
| 404 | Not Found - resource doesn't exist |
| 409 | Conflict - resource not ready |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Common Error Responses

**400 - Invalid Input**
```json
{"detail": "Unsupported file type"}
{"detail": "File exceeds 10 MB limit"}
{"detail": "Document exceeds 50 pages/slides"}
{"detail": "Password must contain at least one uppercase letter"}
{"detail": "Password must contain at least one digit"}
```

**401 - Authentication Failed**
```json
{"detail": "Invalid or expired token"}
{"detail": "Invalid credentials"}
```

**403 - Access Denied**
```json
{"detail": "Free trial document limit reached"}
```

**404 - Not Found**
```json
{"detail": "Document not found"}
```

**409 - Conflict**
```json
{"detail": "Document processing not complete"}
```

**503 - Service Unavailable**
```json
{"detail": "Storage service temporarily unavailable"}
{"detail": "Service temporarily unavailable"}
```

---

## Code Examples

### JavaScript / TypeScript

```javascript
const BASE_URL = 'http://localhost:8000';

// 1. Sign Up
async function signup(email, password) {
  const response = await fetch(`${BASE_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
}

// 2. Login
async function login(email, password) {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  if (!response.ok) {
    throw new Error('Invalid credentials');
  }
  
  const data = await response.json();
  return data.access_token;
}

// 3. Upload Document
async function uploadDocument(file, token) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${BASE_URL}/documents`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json(); // { document_id, status }
}

// 4. List Documents
async function listDocuments(token) {
  const response = await fetch(`${BASE_URL}/documents`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  
  return response.json();
}

// 5. Get Status
async function getStatus(documentId, token) {
  const response = await fetch(
    `${BASE_URL}/documents/${documentId}/status`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  
  return response.json(); // { status }
}

// 6. Get Lessons
async function getLessons(documentId, token) {
  const response = await fetch(
    `${BASE_URL}/documents/${documentId}/lessons`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  
  if (response.status === 409) {
    throw new Error('Document processing not complete');
  }
  
  return response.json(); // Array of fact/mcq items
}

// Complete Upload Flow Example
async function processDocument(file) {
  // Step 1: Login (or use stored token)
  const token = await login('user@example.com', 'SecurePass123');
  
  // Step 2: Upload
  const { document_id, status } = await uploadDocument(file, token);
  console.log('Uploaded, status:', status);
  
  // Step 3: Poll for completion
  const completed = await waitForCompletion(document_id, token);
  
  if (!completed) {
    throw new Error('Processing failed');
  }
  
  // Step 4: Get lessons
  const lessons = await getLessons(document_id, token);
  console.log(`Got ${lessons.length} lessons`);
  
  return lessons;
}
```

### React Example (Custom Hook)

```javascript
import { useState, useCallback } from 'react';

export function useMicrolearnApi() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  const api = useCallback(async (endpoint, options = {}) => {
    const headers = {
      ...options.headers,
    };
    
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    
    const response = await fetch(`http://localhost:8000${endpoint}`, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      localStorage.removeItem('token');
      setToken(null);
      throw new Error('Session expired');
    }
    
    return response;
  }, [token]);
  
  return { api, setToken };
}

// Usage in component
function DocumentUploader() {
  const { api, setToken } = useMicrolearnApi();
  
  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api('/documents', {
      method: 'POST',
      body: formData,
    });
    
    return response.json();
  };
  
  // ... rest of component
}
```

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8000"

class MicrolearnClient:
    def __init__(self):
        self.token = None
    
    def login(self, email: str, password: str) -> str:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
        return self.token
    
    def upload(self, filepath: str) -> dict:
        with open(filepath, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/documents",
                files={"file": f},
                headers={"Authorization": f"Bearer {self.token}"}
            )
        response.raise_for_status()
        return response.json()
    
    def get_lessons(self, document_id: str) -> list:
        response = requests.get(
            f"{BASE_URL}/documents/{document_id}/lessons",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        response.raise_for_status()
        return response.json()


# Usage
client = MicrolearnClient()
client.login("user@example.com", "SecurePass123")
result = client.upload("lecture.pdf")
print(result)  # {"document_id": "...", "status": "pending"}

# Poll status
import time
while True:
    status = requests.get(
        f"{BASE_URL}/documents/{result['document_id']}/status",
        headers={"Authorization": f"Bearer {client.token}"}
    ).json()
    print(status)
    if status["status"] == "completed":
        break
    time.sleep(3)

# Get lessons
lessons = client.get_lessons(result["document_id"])
print(f"Got {len(lessons)} lessons")
```

---

## Testing with cURL

```bash
# 1. Sign up
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123"}'

# 2. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123"}'
# Response: {"access_token":"...","token_type":"bearer"}

# 3. Upload document
curl -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "file=@/path/to/document.pdf"

# 4. List documents
curl -X GET http://localhost:8000/documents \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# 5. Check status
curl -X GET http://localhost:8000/documents/DOC_ID/status \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# 6. Get lessons
curl -X GET http://localhost:8000/documents/DOC_ID/lessons \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Notes for Frontend Integration

1. **Store Token Securely**: Use httpOnly cookies or secure storage; avoid localStorage for sensitive apps
2. **Handle 401 Gracefully**: Implement token refresh or redirect to login
3. **Poll with Backoff**: Start with 2-second intervals, increase to 5 seconds
4. **Show Progress**: Display pending/processing status to user
5. **Validate Before Upload**: Check file type client-side to avoid wasted uploads
6. **Handle Large Files**: Show upload progress for files approaching 10MB

---

## Support

For issues or questions, refer to the project documentation or open an issue in the repository.
