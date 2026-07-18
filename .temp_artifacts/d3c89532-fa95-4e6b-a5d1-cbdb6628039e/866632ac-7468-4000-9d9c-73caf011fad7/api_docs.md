openapi: 3.0.0
info:
  title: Mock API
  version: 1.0.0
paths:
  /api/v1/health:
    get:
      summary: Health check
      responses:
        '200':
          description: Success