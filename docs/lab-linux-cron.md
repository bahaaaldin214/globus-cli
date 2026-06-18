# Lab Linux Cron Setup

The lab Linux machine sees the Windows `Z:\` share at:

```bash
/mnt/nfs/lss/vosslabhpc
```

The shared tools installer is therefore:

```bash
bash /mnt/nfs/lss/vosslabhpc/Users/bahaa/tools/install.sh
source ~/.bashrc
```

Run that once interactively, then verify the Globus helper can authenticate and find the
expected files:

```bash
globus whoami
/mnt/nfs/lss/vosslabhpc/Users/bahaa/tools/globus/globus_cli_dry_run.sh sync
/mnt/nfs/lss/vosslabhpc/Users/bahaa/tools/globus/globus_cli_dry_run.sh transfer
```

After the dry runs look right, install a morning cron entry with `crontab -e`:

```cron
SHELL=/bin/bash
PATH=/home/bmohammad/.local/bin:/usr/local/bin:/usr/bin:/bin

0 6 * * * /mnt/nfs/lss/vosslabhpc/Users/bahaa/tools/globus/globus_cli_run.sh both >> /mnt/nfs/lss/vosslabhpc/Users/bahaa/logs/globus-cron.log 2>&1
```

Use the account that ran `globus login`; Globus CLI auth is user-specific. If the lab
Linux machine uses a different home directory than `/home/bmohammad`, update `PATH`
to include that user's local Python/bin directory.

Useful checks:

```bash
crontab -l
tail -n 80 /mnt/nfs/lss/vosslabhpc/Users/bahaa/logs/globus-cron.log
globus task list --limit 5
```
