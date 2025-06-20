# Vaani Backend

A FastAPI-based backend service for book authors' text autocomplete functionality.

## Setup

1. Create a `.env` file in the root directory with your OpenAI API key:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

2. Build and run the application using Docker Compose:

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

- Interactive API docs (Swagger UI): `http://localhost:8000/docs`
- Alternative API docs (ReDoc): `http://localhost:8000/redoc`

## Available Endpoints

### Books

#### Get All Books

```bash
curl -X GET "http://localhost:8000/books"
```

#### Get Book by ID

```bash
curl -X GET "http://localhost:8000/books/{book_id}"
```

#### Create New Book

```bash
curl -X POST "http://localhost:8000/books" \
-H "Content-Type: application/json" \
-d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald"
}'
```

### Chapters

#### Get All Chapters for a Book

```bash
curl -X GET "http://localhost:8000/books/{book_id}/chapters"
```

#### Get Chapter by ID

```bash
curl -X GET "http://localhost:8000/books/{book_id}/chapters/{chapter_id}"
```

#### Create New Chapter

```bash
curl -X POST "http://localhost:8000/books/{book_id}/chapters" \
-H "Content-Type: application/json" \
-d '{
    "title": "Chapter 1",
    "chapter_no": 1,
    "content": "In my younger and more vulnerable years..."
}'
```

#### Update Chapter Content

```bash
curl -X PUT "http://localhost:8000/books/{book_id}/chapters/{chapter_id}" \
-H "Content-Type: application/json" \
-d '{
    "content": "Updated chapter content..."
}'
```

### Story Completion

#### Stream Story Completion

```bash
curl -N -X POST "http://localhost:8000/complete" \
-H "Content-Type: application/json" \
-d '{
    "context": "The sun was setting over the mountains, casting long shadows across the valley. Sarah stood at the edge of the cliff, her heart pounding with anticipation.",
    "user_prompt": "Continue the story with Sarah making a decision"
}'
```

Note: The `-N` flag in curl prevents buffering, which is important for streaming responses.

### Testing

#### Test Database Connection

```bash
curl -X GET "http://localhost:8000/books/test"
```

## Response Formats

### Book Response

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald"
}
```

### Chapter Response

```json
{
  "id": 1,
  "book_id": 1,
  "title": "Chapter 1",
  "chapter_no": 1,
  "content": "Chapter content..."
}
```

### Completion Stream Response

```
data: {"content": "generated text chunk"}
data: {"content": "next chunk"}
...
data: [DONE]
```

## Error Handling

The API returns appropriate HTTP status codes:

- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses include a detail message:

```json
{
  "detail": "Error message description"
}
```

## Development

This is a basic setup for the Vaani backend. Future development will include:

- User authentication
- Rate limiting
- Advanced text processing and analysis
- Book metadata management
- User preferences and settings
