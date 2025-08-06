# Email Image Display Troubleshooting

## Problem
Thumbnail images were not displaying in the email client when using simple base64 data URLs.

## Root Cause
Many email clients (especially Gmail, Outlook, and enterprise email systems) block inline base64 images embedded as data URLs for security reasons. This is a common email client restriction.

## Solution Implemented
Changed from simple data URL embedding to proper MIME multipart email structure with Content-ID references:

### Previous Method (Blocked by many clients):
```html
<img src="data:image/jpeg;base64,/9j/4AAQ..." />
```

### New Method (Industry standard):
```html
<img src="cid:image0@frigate" />
```

With the image attached as a MIME part with matching Content-ID.

## Technical Implementation

1. **Email Structure**: Changed to `multipart/related` MIME type
2. **Image References**: Each image gets a unique Content-ID (e.g., `image0@frigate`)
3. **Image Attachments**: Images attached as `MIMEImage` parts with:
   - `Content-ID` header matching the HTML reference
   - `Content-Disposition: inline` for embedding
4. **Fallback**: Plain text alternative for clients that don't support HTML

## Benefits
- **Better Compatibility**: Works with Gmail, Outlook, Apple Mail, etc.
- **Security Compliant**: Passes email security filters
- **Professional Standard**: Industry-standard way to embed images
- **Reliable Display**: Images more likely to display automatically

## Email Client Compatibility

| Client | Data URL Support | Content-ID Support |
|--------|-----------------|-------------------|
| Gmail | ❌ Blocked | ✅ Full |
| Outlook | ❌ Blocked | ✅ Full |
| Apple Mail | ⚠️ Limited | ✅ Full |
| Thunderbird | ✅ Full | ✅ Full |
| Mobile Clients | ❌ Usually blocked | ✅ Full |

## Testing
To verify images are properly embedded:

1. Check the email source for `Content-ID` headers
2. Look for `multipart/related` content type
3. Verify each image has a corresponding CID reference

## If Images Still Don't Display

1. **Check Email Client Settings**: 
   - Enable "Display Images" or "Download Images"
   - Add sender to trusted/safe senders list

2. **Security Software**: 
   - Corporate firewalls may strip images
   - Anti-virus may block embedded content

3. **Email Size**: 
   - Some servers reject emails over 10MB
   - Our thumbnails are ~8KB each, so this shouldn't be an issue

## Alternative Approaches (if needed)

1. **External Hosting**: Host images on a web server and link to them
2. **Attachment Only**: Include images as regular attachments
3. **PDF Report**: Generate a PDF with embedded images
4. **Web View**: Link to a web-based report viewer

The current Content-ID implementation should work for 95% of email clients and use cases.
