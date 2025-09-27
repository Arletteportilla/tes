# Public API Testing Configuration

## Overview

The Sistema de Polinización y Germinación includes a special configuration for API testing that allows temporary public access to endpoints without authentication. This feature is designed exclusively for development and testing purposes.

## ⚠️ Security Warning

**NEVER enable public API testing in production environments!**

This feature completely bypasses authentication and authorization for most endpoints, making all data publicly accessible.

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Enable public API testing (development only)
ENABLE_PUBLIC_API_TESTING=True
DEBUG=True
```

### Management Command

Use the management command to toggle the setting:

```bash
# Enable public API testing
python manage.py toggle_public_api --enable

# Disable public API testing
python manage.py toggle_public_api --disable

# Check current status
python manage.py toggle_public_api --status
```

## How It Works

When public API testing is enabled:

1. **Most endpoints become public**: No authentication required
2. **Authentication endpoints remain protected**: Login still requires valid credentials
3. **Headers added**: Special headers indicate testing mode
4. **Documentation updated**: Swagger docs show testing mode warning

### Protected Endpoints (Always Require Authentication)

Even in public testing mode, these endpoints still require valid credentials:

- `POST /api/auth/login/` - User login
- `POST /api/auth/token/` - JWT token obtain
- `POST /api/auth/token/refresh/` - JWT token refresh

### Public Endpoints (When Testing Mode Enabled)

All other endpoints become publicly accessible:

- `/api/pollination/` - Pollination records
- `/api/germination/` - Germination records
- `/api/alerts/` - Alerts and notifications
- `/api/reports/` - Reports (admin features)
- `/api/system/` - System information

## Testing the Configuration

### Check System Status

```bash
curl http://localhost:8000/api/system/testing-status/
```

Response when public testing is enabled:
```json
{
    "debug_mode": true,
    "public_api_testing": true,
    "authentication_required": false,
    "message": "APIs públicas habilitadas para testing",
    "warning": "Este modo NO debe usarse en producción"
}
```

### Test Public Access

```bash
# This should work without authentication when public testing is enabled
curl http://localhost:8000/api/pollination/plants/

# This should still require authentication
curl http://localhost:8000/api/auth/login/
```

### Response Headers

When public testing is enabled, responses include these headers:

```
X-API-Testing-Mode: public
X-Authentication-Required: false
X-Warning: Development mode - APIs publicly accessible
```

## Swagger Documentation

When public testing is enabled, the Swagger documentation at `/api/docs/` will show:

1. **Warning banner** about public testing mode
2. **Updated description** explaining which endpoints are public
3. **Security schemes** still documented for reference

## Implementation Details

### Custom Permission Class

The system uses `core.permissions.PublicAPITestingPermission` which:

- Only allows public access when `DEBUG=True`
- Requires explicit `ENABLE_PUBLIC_API_TESTING=True` setting
- Returns `False` for any production environment

### Middleware

`core.middleware.PublicAPITestingMiddleware` adds response headers to indicate the current testing mode.

### ViewSet Integration

ViewSets can use the `AuthenticationBypassMixin` to automatically handle testing mode:

```python
from core.permissions import AuthenticationBypassMixin

class MyViewSet(AuthenticationBypassMixin, viewsets.ModelViewSet):
    # This ViewSet will automatically use public permissions in testing mode
    pass
```

## Best Practices

### For Development

1. **Enable for API exploration**: Use public testing to explore APIs with tools like Postman
2. **Frontend development**: Develop frontend without authentication complexity
3. **Integration testing**: Test API integrations without token management

### For Testing

1. **Automated tests**: Write tests that work in both modes
2. **CI/CD pipelines**: Ensure tests pass with authentication enabled
3. **Security testing**: Test that production mode properly requires authentication

### Security Checklist

- [ ] `DEBUG=False` in production
- [ ] `ENABLE_PUBLIC_API_TESTING=False` or not set in production
- [ ] Environment variables properly configured
- [ ] Production deployment scripts don't include testing settings

## Troubleshooting

### Public Testing Not Working

1. Check `DEBUG=True` in settings
2. Verify `ENABLE_PUBLIC_API_TESTING=True` in environment
3. Restart Django server after changing settings
4. Check `/api/system/testing-status/` endpoint

### Authentication Still Required

1. Verify environment variables are loaded
2. Check middleware is properly configured
3. Ensure ViewSets use correct permission classes
4. Check for custom permission overrides

### Production Accidentally Public

1. Immediately set `DEBUG=False`
2. Remove or set `ENABLE_PUBLIC_API_TESTING=False`
3. Restart all application servers
4. Verify with `/api/system/testing-status/` endpoint

## Related Files

- `core/permissions.py` - Custom permission classes
- `core/middleware.py` - Testing mode middleware
- `core/views.py` - System status endpoints
- `core/management/commands/toggle_public_api.py` - Management command
- `sistema_polinizacion/settings.py` - Configuration settings