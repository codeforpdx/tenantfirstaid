# Persistent Data Storage

The application now stores persistent data (chatlog.jsonl) in a dedicated directory:

```
/root/tenantfirstaid_data/
```

You can override this by setting `PERSISTENT_STORAGE_DIR` in `.env`.

## Data Files

The following files are stored persistently:

1. **Chat Logs**: `/root/tenantfirstaid_data/chatlog.jsonl`
   - Contains all chat interactions for training and analysis
   - Automatically appended to after each conversation

## Benefits

- Data survives application updates and deployments
- Consistent location for backups
- Prevents data loss when the application directory is overwritten

## Backup Recommendations

Periodically back up the `/root/tenantfirstaid_data/` directory to prevent data loss:

```bash
# Example backup command
tar -czf /root/tenantfirstaid_backups/data_backup_$(date +%Y%m%d).tar.gz /root/tenantfirstaid_data/
```

This change ensures that valuable conversation data is preserved even when the application code is updated or the server is redeployed.